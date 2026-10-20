"""Invented records exercise story logic and integrity, never scientific results."""

import hashlib
import json

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pitching.phase2_dashboard import load_phase2_reports
from pitching.research_story import preview_example, primary_story_summary


def _bind(root):
    directory = root / "phase2"
    artifacts = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.iterdir()
        if path.is_file() and path.name != "run_metadata.json"
    }
    analysis_hash = hashlib.sha256((root / "analysis.csv").read_bytes()).hexdigest()
    child = {
        "status": "completed",
        "fixture": "synthetic software test; not observed biomechanics data",
        "analysis_sha256": analysis_hash,
        "artifacts_sha256": artifacts,
    }
    marker = directory / "run_metadata.json"
    marker.write_text(json.dumps(child))
    artifacts["run_metadata.json"] = hashlib.sha256(marker.read_bytes()).hexdigest()
    parent = {
        "status": "completed",
        "artifacts_sha256": {
            "analysis.csv": analysis_hash,
            **{f"phase2/{name}": digest for name, digest in artifacts.items()},
        },
    }
    (root / "run_metadata.json").write_text(json.dumps(parent))


@pytest.fixture
def story_reports(tmp_path):
    directory = tmp_path / "phase2"
    directory.mkdir()
    pd.DataFrame(
        {
            "session_pitch": ["synthetic-p1", "synthetic-p2", "synthetic-p3", "synthetic-p4"],
            "user": ["synthetic-a", "synthetic-a", "synthetic-b", "synthetic-b"],
            "pitch_speed_mph": [75.0, 77.0, 82.0, 84.0],
        }
    ).to_csv(tmp_path / "analysis.csv", index=False)
    models = ["dummy_mean", "ridge_anthropometric", "ridge_kinematic", "ridge_combined"]
    targets = ["pitch_speed_mph", "elbow_varus_moment"]
    scores, sensitivity, athletes, comparisons = [], [], [], []
    for target_index, target in enumerate(targets, start=1):
        for model, error in zip(models, [4.0, 3.0, 3.5, 2.0]):
            row = {
                "target": target,
                "model": model,
                "n_pitches": 4,
                "n_athletes": 2,
                "mae": error * target_index,
                "athlete_mae": error * target_index,
                "rmse": error * target_index + 0.5,
                "r2": 0.2,
            }
            scores.append(row)
            for seed in [42, 43]:
                sensitivity.append({**row, "partition_seed": seed})
            for athlete in ["synthetic-a", "synthetic-b"]:
                athletes.append(
                    {
                        "target": target,
                        "model": model,
                        "user": athlete,
                        "n_pitches": 2,
                        "mae": error * target_index,
                    }
                )
        for metric in ["athlete_mae", "mae"]:
            comparisons.append(
                {
                    "target": target,
                    "model": "ridge_combined",
                    "reference": "ridge_anthropometric",
                    "metric": metric,
                    "estimate": -float(target_index),
                    "ci_low": -1.5 * target_index,
                    "ci_high": -0.5 if target_index == 1 else 0.5,
                    "n_athletes": 2,
                    "bootstrap_replicates": 100,
                    "confidence_level": 0.95,
                }
            )
    for name, data in [
        ("phase2_model_metrics.csv", scores),
        ("phase2_sensitivity_metrics.csv", sensitivity),
        ("phase2_comparisons.csv", comparisons),
        ("phase2_athlete_errors.csv", athletes),
    ]:
        pd.DataFrame(data).to_csv(directory / name, index=False)
    (directory / "phase2_model_spec.json").write_text(
        json.dumps({"bootstrap": {"confidence_level": 0.95}, "fixture": "synthetic"})
    )
    (directory / "phase2_report.md").write_text("Synthetic software test report only.\n")
    _bind(tmp_path)
    return tmp_path


def _start(root, project=None):
    project = project or root
    return AppTest.from_string(
        "from pathlib import Path\n"
        "import pandas as pd\n"
        "import streamlit as st\n"
        "from pitching.research_story import render_start\n"
        f"root = Path({str(root)!r})\n"
        "def navigate(page):\n"
        "    st.session_state['destination'] = page\n"
        "frame = pd.read_csv(root/'analysis.csv', dtype={'session_pitch': str, 'user': str})\n"
        f"render_start(frame, Path({str(project)!r}), root, navigate)\n",
        default_timeout=30,
    ).run()


def _study(root):
    return AppTest.from_string(
        "from pathlib import Path\n"
        "from pitching.research_story import render_study_story\n"
        f"render_study_story(Path({str(root)!r}))\n",
        default_timeout=30,
    ).run()


def test_summary_preserves_units_scores_and_conditional_uncertainty(story_reports):
    reports = load_phase2_reports(story_reports)
    speed = primary_story_summary(reports, "pitch_speed_mph")
    assert speed.unit == "mph"
    assert speed.body_error == 3 and speed.combined_error == 2 and speed.difference == -1
    assert "lowered observed prediction error" in speed.finding
    elbow = primary_story_summary(reports, "elbow_varus_moment")
    assert elbow.unit == "N·m" and elbow.interval_includes_zero
    assert "added predictive value remains uncertain" in elbow.finding


def test_unfavorable_result_is_not_rewritten_as_a_benefit(story_reports):
    path = story_reports / "phase2/phase2_model_metrics.csv"
    scores = pd.read_csv(path)
    scores.loc[scores.model.eq("ridge_combined"), ["mae", "athlete_mae"]] = [6.0, 6.0]
    scores.to_csv(path, index=False)
    path = story_reports / "phase2/phase2_comparisons.csv"
    comparisons = pd.read_csv(path)
    for target, difference in [("pitch_speed_mph", 3.0), ("elbow_varus_moment", 0.0)]:
        index = comparisons.target.eq(target)
        comparisons.loc[index, "estimate"] = difference
        comparisons.loc[index, "ci_low"] = difference - 0.5
        comparisons.loc[index, "ci_high"] = difference + 0.5
    comparisons.to_csv(path, index=False)
    _bind(story_reports)
    summary = primary_story_summary(load_phase2_reports(story_reports), "pitch_speed_mph")
    assert "increased observed prediction error by 3.00 mph" in summary.finding


def test_inconsistent_saved_difference_cannot_become_a_story(story_reports):
    path = story_reports / "phase2/phase2_comparisons.csv"
    comparisons = pd.read_csv(path)
    comparisons["estimate"] = -99
    comparisons.to_csv(path, index=False)
    _bind(story_reports)
    with pytest.raises(ValueError, match="differs from its model errors"):
        primary_story_summary(load_phase2_reports(story_reports), "pitch_speed_mph")


def test_home_uses_actual_counts_and_navigation_callbacks(story_reports):
    app = _start(story_reports)
    assert not app.exception
    metrics = {item.label: item.value for item in app.metric}
    assert any("**4 recorded pitches · 2 athletes**" == item.value for item in app.markdown)
    assert metrics["Age + body size"] == "3.00 mph"
    app.button(key="story_open_explore").click().run()
    assert app.session_state["destination"] == "Explore pitches"
    app.radio(key="story_target").set_value("elbow_varus_moment").run()
    assert not app.exception
    assert any("predictive value remains uncertain" in item.value for item in app.markdown)


def test_corrupted_report_hides_results_in_both_views(story_reports):
    path = story_reports / "phase2/phase2_model_metrics.csv"
    path.write_bytes(path.read_bytes() + b"changed")
    for app in [_start(story_reports), _study(story_reports)]:
        assert not app.exception
        assert any("Findings are hidden" in item.value for item in app.warning)
        assert "Add rotational measures" not in {item.label for item in app.metric}


def test_study_has_usable_outcome_and_four_model_controls(story_reports):
    app = _study(story_reports)
    assert not app.exception
    assert app.radio(key="study_story_target").value == "pitch_speed_mph"
    app.toggle(key="study_story_all_models").set_value(True).run()
    app.radio(key="study_story_target").set_value("elbow_varus_moment").run()
    assert not app.exception
    metrics = {item.label: item.value for item in app.metric}
    assert metrics["Add rotational measures"] == "4.00 N·m"
    assert any("excludes uncertainty from retraining" in item.value for item in app.caption)


def test_preview_requires_both_pitch_and_athlete_and_selects_middle_recorded_speed():
    frame = pd.DataFrame(
        {
            "session_pitch": ["a", "b", "c"],
            "user": ["athlete-a", "athlete-b", "athlete-c"],
            "pitch_speed_mph": [70.0, 85.0, 94.0],
        }
    )
    entries = [
        {"session_pitch": pitch, "user": user}
        for pitch, user in frame[["session_pitch", "user"]].itertuples(index=False, name=None)
    ]
    assert preview_example(frame, entries)["session_pitch"] == "b"
    assert preview_example(frame, [{"session_pitch": "b", "user": "other-athlete"}]) is None
