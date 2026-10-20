"""Research-report scope, missingness, input integrity, and safe standalone output."""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pitching.athlete_reports import (
    matched_predictions,
    prepare_athlete_report,
    render_report_html,
    report_csv,
    report_metadata_json,
)
from pitching.data import VARIABLES
from pitching.phase2_dashboard import load_phase2_reports

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def study():
    return load_phase2_reports(ROOT / "assets/demo/reports")


@pytest.fixture
def observations():
    frame = pd.DataFrame(
        {
            "session_pitch": ["a_1", "a_2", "a_3", "b_1"],
            "user": ["a", "a", "a", "b"],
            "session": ["assessment-a"] * 3 + ["assessment-b"],
        }
    )
    for column in VARIABLES:
        frame[column] = [10.0, 20.0, np.nan, 1000.0]
    return frame


def test_scope_is_one_athletes_observed_pitches_and_missingness_is_retained(observations):
    report = prepare_athlete_report(observations, "a")
    assert len(report.pitches) == 3
    assert report.metadata["n_sessions"] == 1
    assert report.metadata["supplied_table_athletes"] == 2
    assert report.summary["mean"].tolist() == [15.0] * 5
    assert report.summary["n_observed"].tolist() == [2] * 5
    assert report.summary["n_missing"].tolist() == [1] * 5
    assert report.predictions.empty
    assert any("one released assessment" in notice for notice in report.notices)
    exported = pd.read_csv(BytesIO(report_csv(report).encode()))
    assert exported["pitch_speed_mph"].isna().sum() == 1
    assert (
        report.metadata["observations_csv_sha256"]
        == hashlib.sha256(report_csv(report).encode()).hexdigest()
    )


def test_completely_missing_measurement_is_not_a_zero(observations):
    observations["elbow_varus_moment"] = np.nan
    report = prepare_athlete_report(observations, "a")
    summary = report.summary.set_index("variable").loc["elbow_varus_moment"]
    assert summary.n_observed == 0
    assert summary.n_missing == 3
    assert pd.isna(summary["mean"])
    assert "No observed values for this measurement" in render_report_html(report)


def test_blank_session_does_not_establish_one_observed_assessment(observations):
    observations.loc[0, "session"] = " "
    report = prepare_athlete_report(observations, "a")
    assert report.metadata["n_sessions"] is None
    assert any("does not establish complete session" in notice for notice in report.notices)


def test_csv_formula_identifiers_are_escaped_with_originals_in_metadata(observations):
    observations.loc[0, "session_pitch"] = '=HYPERLINK("https://example.invalid")'
    observations.loc[1, "session_pitch"] = "  +12"
    observations.loc[0, "elbow_varus_moment"] = -4.5
    report = prepare_athlete_report(observations, "a")
    exported = pd.read_csv(BytesIO(report_csv(report).encode()), dtype={"session_pitch": "string"})
    assert set(exported.session_pitch) == {
        "'  +12",
        '\'=HYPERLINK("https://example.invalid")',
        "a_3",
    }
    assert -4.5 in set(exported.elbow_varus_moment.dropna())
    metadata = json.loads(report_metadata_json(report))
    assert len(metadata["csv_identifier_escapes"]) == 2
    assert {item["original"] for item in metadata["csv_identifier_escapes"]} == {
        '=HYPERLINK("https://example.invalid")',
        "  +12",
    }
    assert (
        metadata["observations_csv_sha256"]
        == hashlib.sha256(report_csv(report).encode()).hexdigest()
    )
    assert "protective apostrophe prefix" in render_report_html(report)


@pytest.mark.parametrize("problem", ["duplicate", "empty_id", "missing_user", "text", "infinity"])
def test_report_rejects_invalid_observation_tables(observations, problem):
    if problem == "duplicate":
        observations.loc[1, "session_pitch"] = observations.loc[0, "session_pitch"]
    elif problem == "empty_id":
        observations.loc[0, "session_pitch"] = " "
    elif problem == "missing_user":
        observations.loc[0, "user"] = None
    elif problem == "text":
        observations["pitch_speed_mph"] = ["unknown"] * 4
    else:
        observations.loc[0, "pitch_speed_mph"] = np.inf
    with pytest.raises(ValueError):
        prepare_athlete_report(observations, "a")


def test_report_html_escapes_identifiers_and_has_no_remote_assets_or_scripts(observations):
    hostile = '</title><script>alert("player")</script>'
    observations.loc[observations.user.eq("a"), "user"] = hostile
    observations.loc[0, "session_pitch"] = '<svg onload="alert(1)">'
    report = prepare_athlete_report(observations, hostile)
    html = render_report_html(report)
    assert "<script" not in html.lower()
    assert '<svg onload="' not in html
    assert "&lt;script&gt;" in html
    assert "<img" not in html and "<link" not in html
    assert "@media print" in html and 'name="viewport"' in html
    assert "professional-sports" in html
    assert "source identity has not been verified" in html


def test_report_uses_verified_primary_combined_errors_and_preserves_subset_scope(study):
    subset = study.analysis.loc[study.analysis.user.eq("970")].iloc[:2]
    report = prepare_athlete_report(subset, "970", study)
    assert report.metadata["reference_identity_and_measurements_verified"] is True
    assert report.metadata["reference_athlete_pitches_available"] == 3
    assert report.metadata["primary_partition_seed"] == 42
    assert len(report.predictions) == 4
    assert set(report.predictions.session_pitch) == set(subset.session_pitch)
    assert np.allclose(
        report.predictions.absolute_error,
        abs(report.predictions.observed - report.predictions.predicted),
    )
    html = render_report_html(report)
    assert "2 of 3 pitches" in html
    assert "athlete-held-out combined ridge" in html
    metadata = json.loads(report_metadata_json(report))
    assert metadata["verified_study_analysis_sha256"] == study.metadata["analysis_sha256"]


def test_changed_measured_outcome_withholds_saved_errors_and_source_claim(study):
    subset = study.analysis.loc[study.analysis.user.eq("970")].copy()
    subset.loc[subset.index[0], "pitch_speed_mph"] += 0.5
    report = prepare_athlete_report(subset, "970", study)
    assert report.predictions.empty
    assert report.metadata["reference_identity_and_measurements_verified"] is False
    assert report.metadata["source_commit"] is None
    assert any("withheld" in notice for notice in report.notices)


@pytest.mark.parametrize("problem", ["user", "fold", "observed", "residual", "duplicate"])
def test_inconsistent_saved_prediction_rows_cannot_be_rendered_as_verified(study, problem):
    raw = pd.read_csv(
        BytesIO(study.verified_bytes["phase2_oof_predictions.csv"]),
        dtype={"user": "string", "session_pitch": "string"},
    )
    selected_index = raw.index[raw.user.eq("970") & raw.model.eq("ridge_combined")][0]
    if problem == "duplicate":
        raw = pd.concat([raw, raw.loc[[selected_index]]], ignore_index=True)
    elif problem == "user":
        raw.loc[selected_index, "user"] = "different-athlete"
    elif problem == "fold":
        raw.loc[selected_index, "fold"] = 999
    else:
        raw.loc[selected_index, problem] += 0.25
    modified = replace(
        study,
        verified_bytes={
            **study.verified_bytes,
            "phase2_oof_predictions.csv": raw.to_csv(index=False).encode(),
        },
    )
    selected = study.analysis.loc[study.analysis.user.eq("970")].copy()
    with pytest.raises(ValueError):
        matched_predictions(selected, modified)
    assert prepare_athlete_report(selected, "970", modified).predictions.empty


def test_creation_time_is_explicit_and_metadata_is_json_safe(observations):
    created = datetime(2026, 10, 20, 12, 30, tzinfo=UTC)
    report = prepare_athlete_report(observations, "a", created_utc=created)
    assert json.loads(report_metadata_json(report))["created_utc"] == created.isoformat()
    with pytest.raises(ValueError, match="timezone"):
        prepare_athlete_report(observations, "a", created_utc=datetime(2026, 10, 20))


def test_report_cross_link_is_consumed_once_and_consecutive_choices_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A report rerun must not fit models or fetch data")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("pitching.models.evaluate_baselines", forbidden)
    script = f"""
from pathlib import Path
import pandas as pd
import streamlit as st
from pitching.report_dashboard import render_report_builder
root=Path({str(ROOT)!r})
frame=pd.read_csv(root / "assets/demo/reports/analysis.csv",dtype={{"user":"string","session_pitch":"string"}})
render_report_builder(frame,root / "assets/demo/reports",root)
"""
    app = AppTest.from_string(script, default_timeout=30)
    app.session_state["report_requested_athlete"] = "970"
    app.run()
    assert not app.exception, [error.value for error in app.exception]
    assert app.selectbox(key="report_athlete").value == "970"
    for athlete in ["919", "1596", "970"]:
        app.selectbox(key="report_athlete").set_value(athlete).run()
        assert not app.exception, [error.value for error in app.exception]
        assert app.selectbox(key="report_athlete").value == athlete
    assert len(app.get("download_button")) == 3


def test_builder_cards_keep_missing_values_distinct_and_round_display_only(observations, tmp_path):
    observations.loc[0, "pitch_speed_mph"] = 10.123456
    observations.loc[1, "pitch_speed_mph"] = 20.234567
    observations["elbow_varus_moment"] = np.nan
    script = f"""
from io import StringIO
from pathlib import Path
import pandas as pd
from pitching.report_dashboard import render_report_builder
frame=pd.read_csv(StringIO({observations.to_csv(index=False)!r}),dtype={{"user":"string","session_pitch":"string"}})
render_report_builder(frame,Path({str(tmp_path)!r}),Path({str(ROOT)!r}))
"""
    app = AppTest.from_string(script, default_timeout=30).run()
    assert not app.exception, [error.value for error in app.exception]
    metrics = {item.label: item.value for item in app.metric}
    assert metrics[VARIABLES["pitch_speed_mph"][0]] == "15.18 mph"
    assert metrics[VARIABLES["elbow_varus_moment"][0]] == "Unavailable"
    assert any(
        "No observed values in 3 recorded pitches; 3 missing" in item.value for item in app.caption
    )
    assert "Detailed measurement table" in {item.label for item in app.expander}
    detailed = app.dataframe[0].value
    speed = detailed.loc[detailed["Recorded measurement"].eq(VARIABLES["pitch_speed_mph"][0])]
    assert speed["Observed mean"].iloc[0] == pytest.approx((10.123456 + 20.234567) / 2)
    assert len(app.get("download_button")) == 3
