"""Synthetic Phase 2 reports test integrity and full-cohort UI behavior.

Invented records below exercise software only and never enter research outputs.
"""

import hashlib
import json

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pitching.phase2_dashboard import MODELS, TARGETS, load_phase2_reports


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind_reports(root):
    """Bind synthetic artifacts after an intentional fixture edit."""
    phase2 = root / "phase2"
    child = {
        "status": "completed",
        "fixture": "synthetic test data; not research observations",
        "analysis_sha256": digest(root / "analysis.csv"),
        "artifacts_sha256": {
            path.name: digest(path)
            for path in phase2.iterdir()
            if path.name != "run_metadata.json" and path.is_file()
        },
    }
    (phase2 / "run_metadata.json").write_text(json.dumps(child))
    parent = {
        "status": "completed",
        "artifacts_sha256": {
            "analysis.csv": digest(root / "analysis.csv"),
            **{f"phase2/{path.name}": digest(path) for path in phase2.iterdir() if path.is_file()},
        },
    }
    (root / "run_metadata.json").write_text(json.dumps(parent))


@pytest.fixture
def phase2_reports(tmp_path):
    """Four explicitly invented pitches and two athletes, not OBP records."""
    pd.DataFrame(
        {
            "session_pitch": ["synthetic-p1", "synthetic-p2", "synthetic-p3", "synthetic-p4"],
            "user": ["synthetic-a", "synthetic-a", "synthetic-b", "synthetic-b"],
        }
    ).to_csv(tmp_path / "analysis.csv", index=False)
    phase2 = tmp_path / "phase2"
    phase2.mkdir()
    metrics = []
    athletes = []
    comparisons = []
    sensitivity = []
    for target_index, target in enumerate(TARGETS, start=1):
        for model_index, model in enumerate(MODELS):
            error = (4 - model_index) * target_index
            row = {
                "target": target,
                "model": model,
                "n_pitches": 4,
                "n_athletes": 2,
                "mae": error,
                "rmse": error + 0.5,
                "r2": 0.2,
                "athlete_mae": error,
            }
            metrics.append(row)
            for seed in (42, 43, 44):
                sensitivity.append(
                    {**row, "partition_seed": seed, "athlete_mae": error + (seed - 42) / 10}
                )
            for athlete in ("synthetic-a", "synthetic-b"):
                athletes.append(
                    {
                        "target": target,
                        "model": model,
                        "user": athlete,
                        "fold": 0 if athlete.endswith("a") else 1,
                        "n_pitches": 2,
                        "mae": error,
                        "rmse": error + 0.5,
                        "bias": error,
                    }
                )
        for metric in ("athlete_mae", "mae"):
            comparisons.append(
                {
                    "target": target,
                    "model": "ridge_combined",
                    "reference": "ridge_anthropometric",
                    "metric": metric,
                    "estimate": -2 * target_index,
                    "ci_low": -3 * target_index,
                    "ci_high": -target_index,
                    "n_athletes": 2,
                    "bootstrap_replicates": 100,
                    "confidence_level": 0.95,
                }
            )
    for name, rows in (
        ("phase2_model_metrics.csv", metrics),
        ("phase2_comparisons.csv", comparisons),
        ("phase2_sensitivity_metrics.csv", sensitivity),
        ("phase2_athlete_errors.csv", athletes),
    ):
        pd.DataFrame(rows).to_csv(phase2 / name, index=False)
    (phase2 / "phase2_model_spec.json").write_text(
        json.dumps({"fixture": "synthetic", "ridge_alpha": 10, "primary_metric": "athlete_mae"})
    )
    (phase2 / "phase2_report.md").write_text("Synthetic report for software testing only.\n")
    (phase2 / "extra_trace.txt").write_text("An unrendered artifact must still be verified.\n")
    bind_reports(tmp_path)
    return tmp_path


def make_app(root, selected=None):
    app = AppTest.from_string(
        "from pathlib import Path\n"
        "import streamlit as st\n"
        "from pitching.phase2_dashboard import render_phase2\n"
        f"render_phase2(Path({str(root)!r}), st.session_state.get('selected_ids'))\n",
        default_timeout=30,
    )
    if selected is not None:
        app.session_state["selected_ids"] = selected
    return app.run()


def test_loader_verifies_all_artifacts_and_is_read_only(phase2_reports):
    before = {
        path.relative_to(phase2_reports): path.read_bytes()
        for path in phase2_reports.rglob("*")
        if path.is_file()
    }
    reports = load_phase2_reports(phase2_reports)
    assert len(reports.metrics) == 8
    assert len(reports.analysis) == 4
    assert reports.verified_bytes["phase2_report.md"].startswith(b"Synthetic")
    after = {
        path.relative_to(phase2_reports): path.read_bytes()
        for path in phase2_reports.rglob("*")
        if path.is_file()
    }
    assert before == after


@pytest.mark.parametrize(
    "name",
    [
        "analysis.csv",
        "phase2/run_metadata.json",
        "phase2/phase2_model_metrics.csv",
        "phase2/extra_trace.txt",
    ],
)
def test_changed_artifact_cannot_be_shown_as_completed(phase2_reports, name):
    path = phase2_reports / name
    path.write_bytes(path.read_bytes() + b"\nchanged")
    with pytest.raises(ValueError, match="match|checksum|different"):
        load_phase2_reports(phase2_reports)


def test_completed_child_must_belong_to_parent(phase2_reports):
    parent_path = phase2_reports / "run_metadata.json"
    parent = json.loads(parent_path.read_text())
    del parent["artifacts_sha256"]["phase2/phase2_comparisons.csv"]
    parent_path.write_text(json.dumps(parent))
    with pytest.raises(ValueError, match="does not bind"):
        load_phase2_reports(phase2_reports)


def test_child_rejects_a_different_analysis_even_when_parent_hash_matches(phase2_reports):
    marker = phase2_reports / "phase2/run_metadata.json"
    child = json.loads(marker.read_text())
    child["analysis_sha256"] = "0" * 64
    marker.write_text(json.dumps(child))
    parent_path = phase2_reports / "run_metadata.json"
    parent = json.loads(parent_path.read_text())
    parent["artifacts_sha256"]["phase2/run_metadata.json"] = digest(marker)
    parent_path.write_text(json.dumps(parent))
    with pytest.raises(ValueError, match="different analysis"):
        load_phase2_reports(phase2_reports)


@pytest.mark.parametrize(
    "malicious",
    ["../outside.csv", "/tmp/outside.csv", "folder\\outside.csv", "folder/../outside.csv"],
)
def test_unsafe_declared_artifact_paths_are_rejected(phase2_reports, malicious):
    marker = phase2_reports / "phase2/run_metadata.json"
    child = json.loads(marker.read_text())
    child["artifacts_sha256"][malicious] = "0" * 64
    marker.write_text(json.dumps(child))
    parent_path = phase2_reports / "run_metadata.json"
    parent = json.loads(parent_path.read_text())
    parent["artifacts_sha256"]["phase2/run_metadata.json"] = digest(marker)
    parent_path.write_text(json.dumps(parent))
    with pytest.raises(ValueError, match="artifact path"):
        load_phase2_reports(phase2_reports)


def test_even_rehashed_reports_must_include_primary_comparison(phase2_reports):
    path = phase2_reports / "phase2/phase2_comparisons.csv"
    frame = pd.read_csv(path)
    frame = frame[frame.target != "elbow_varus_moment"]
    frame.to_csv(path, index=False)
    bind_reports(phase2_reports)
    with pytest.raises(ValueError, match="primary comparisons"):
        load_phase2_reports(phase2_reports)


def test_missing_reports_show_command_without_writing(tmp_path):
    app = make_app(tmp_path)
    assert not app.exception
    assert any("have not been generated" in item.value for item in app.info)
    assert app.code[0].value == "uv run --frozen pitching phase2"
    assert not list(tmp_path.iterdir())


def test_stale_report_suppresses_every_phase2_result(phase2_reports):
    (phase2_reports / "phase2/extra_trace.txt").write_text("tampered")
    app = make_app(phase2_reports)
    assert not app.exception
    assert any("No Phase 2 results are displayed" in item.value for item in app.warning)
    assert not app.dataframe
    assert not app.selectbox
    assert not app.get("download_button")


def test_full_cohort_comparisons_stay_fixed_when_sidebar_selection_changes(phase2_reports):
    app = make_app(phase2_reports)
    assert not app.exception
    full_metrics = app.dataframe[0].value.copy()
    full_comparisons = app.dataframe[1].value.copy()
    full_ranges = app.dataframe[2].value.copy()
    app.session_state["selected_ids"] = ["synthetic-p1"]
    app.run()
    assert not app.exception
    pd.testing.assert_frame_equal(app.dataframe[0].value, full_metrics)
    pd.testing.assert_frame_equal(app.dataframe[1].value, full_comparisons)
    pd.testing.assert_frame_equal(app.dataframe[2].value, full_ranges)
    athlete_table = next(item.value for item in app.dataframe if "user" in item.value)
    assert set(athlete_table.user) == {"synthetic-a"}
    assert set(athlete_table.n_pitches) == {2}  # Whole athlete, not selected single pitch.
    assert any("4 pitches from 2 athletes" in item.value for item in app.caption)
    assert any(
        "single-athlete confidence intervals are not provided" in item.value for item in app.caption
    )
    app.session_state["selected_ids"] = []
    app.run()
    assert any("No athlete-level rows" in item.value for item in app.info)
    pd.testing.assert_frame_equal(app.dataframe[0].value, full_metrics)


def test_outcome_selector_changes_units_and_rows(phase2_reports):
    app = make_app(phase2_reports)
    app.selectbox(key="phase2_target").select("elbow_varus_moment").run()
    assert not app.exception
    assert "Equal-athlete MAE (N·m)" in app.dataframe[0].value
    comparisons = app.dataframe[1].value
    assert set(comparisons.estimate) == {-4}
    app.radio(key="phase2_interval_metric").set_value("mae").run()
    assert not app.exception
    assert set(app.dataframe[1].value.metric) == {"mae"}


def test_render_never_downloads_refits_or_bootstraps(phase2_reports, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Phase 2 viewing must only read completed offline reports")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("pitching.models.evaluate_baselines", forbidden)
    monkeypatch.setattr("pitching.phase2.evaluate_phase2", forbidden)
    monkeypatch.setattr("pitching.phase2.compare_fixed_predictions", forbidden)
    monkeypatch.setattr("numpy.random.default_rng", forbidden)
    app = make_app(phase2_reports)
    assert not app.exception, [item.value for item in app.exception]
    assert not app.warning
    assert len(app.get("download_button")) == 6


def test_undefined_r2_is_shown_without_rejecting_other_metrics(phase2_reports):
    for name in ("phase2_model_metrics.csv", "phase2_sensitivity_metrics.csv"):
        path = phase2_reports / "phase2" / name
        frame = pd.read_csv(path)
        frame["r2"] = float("nan")
        frame.to_csv(path, index=False)
    bind_reports(phase2_reports)
    app = make_app(phase2_reports)
    assert not app.exception
    assert not app.warning
    assert app.dataframe[0].value["Pooled R²"].isna().all()
    assert app.dataframe[0].value["Equal-athlete MAE (mph)"].notna().all()


def test_interval_level_follows_verified_study_instead_of_hardcoded_label(
    phase2_reports, monkeypatch
):
    path = phase2_reports / "phase2/phase2_comparisons.csv"
    frame = pd.read_csv(path)
    frame["confidence_level"] = 0.90
    frame.to_csv(path, index=False)
    spec_path = phase2_reports / "phase2/phase2_model_spec.json"
    spec = json.loads(spec_path.read_text())
    spec["bootstrap"] = {"confidence_level": 0.90}
    spec_path.write_text(json.dumps(spec))
    bind_reports(phase2_reports)
    plot_titles = []
    monkeypatch.setattr(
        "pitching.phase2_dashboard.st.pyplot",
        lambda figure, **kwargs: plot_titles.append(figure.axes[0].get_title()),
    )
    app = make_app(phase2_reports)
    assert not app.exception
    assert not app.warning
    assert any("90% per-comparison intervals" in item.value for item in app.caption)
    assert any("90% conditional bootstrap intervals" in title for title in plot_titles)
    assert not any("95%" in title for title in plot_titles)
