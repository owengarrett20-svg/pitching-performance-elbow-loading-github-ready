"""UI smoke and filter tests use explicitly synthetic local reports, not OBP data."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def reports(tmp_path, monkeypatch):
    """Four invented test records exercise rendering; they are never research data."""
    monkeypatch.setenv("PITCHING_REPORT_DIR", str(tmp_path))
    analysis = pd.DataFrame(
        {
            "session_pitch": ["p1", "p2", "p3", "p4"],
            "user": ["athlete-a", "athlete-a", "athlete-b", "athlete-b"],
            "playing_level": ["HS", "HS", "College", "College"],
            "pitch_speed_mph": [80.0, 82.0, 88.0, 90.0],
            "elbow_varus_moment": [70.0, 80.0, 100.0, 110.0],
            "max_shoulder_internal_rotational_velo": [4000.0, 4100.0, 4500.0, 4600.0],
            "max_rotation_hip_shoulder_separation": [30.0, None, 40.0, 45.0],
            "max_torso_rotational_velo": [700.0, 750.0, 800.0, 850.0],
        }
    )
    analysis.to_csv(tmp_path / "analysis.csv", index=False)
    rows = []
    for target in ("pitch_speed_mph", "elbow_varus_moment"):
        for model in ("dummy_mean", "ridge"):
            for index, pitch in analysis.iterrows():
                # athlete-a errors = 1; athlete-b errors = 3. This lets a filter
                # test distinguish selected errors from the complete report.
                residual = 1.0 if index < 2 else 3.0
                observed = pitch[target]
                rows.append(
                    {
                        "session_pitch": pitch["session_pitch"],
                        "user": pitch["user"],
                        "fold": index // 2,
                        "target": target,
                        "model": model,
                        "observed": observed,
                        "predicted": observed - residual,
                        "residual": residual,
                        "absolute_error": residual,
                    }
                )
    pd.DataFrame(rows).to_csv(tmp_path / "oof_predictions.csv", index=False)
    pd.DataFrame(
        [
            {
                "target": target,
                "model": model,
                "n_pitches": 4,
                "n_athletes": 2,
                "mae": 2.0,
                "rmse": 2.236,
                "r2": 0.8,
                "athlete_mae": 2.0,
            }
            for target in ("pitch_speed_mph", "elbow_varus_moment")
            for model in ("dummy_mean", "ridge")
        ]
    ).to_csv(tmp_path / "model_metrics.csv", index=False)
    pd.DataFrame(
        [
            {
                "table": "poi",
                "column": "max_rotation_hip_shoulder_separation",
                "n_rows": 4,
                "n_missing": 1,
                "pct_missing": 25.0,
            }
        ]
    ).to_csv(tmp_path / "missingness.csv", index=False)
    (tmp_path / "audit.json").write_text(
        '{"fixture": "synthetic", "join_cardinality": "one_to_one"}'
    )
    (tmp_path / "run_metadata.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "artifacts_sha256": {
                    name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
                    for name in ("analysis.csv", "oof_predictions.csv", "model_metrics.csv")
                },
            }
        )
    )
    return tmp_path


def metric_values(app):
    return {metric.label: metric.value for metric in app.metric}


def open_error_view(app):
    app.radio(key="app_page").set_value("Study results").run()
    app.radio(key="study_mode").set_value("Prediction errors").run()
    return app


def test_missing_reports_gives_runnable_command(tmp_path, monkeypatch):
    monkeypatch.setenv("PITCHING_REPORT_DIR", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    assert any("No local analysis report" in message.value for message in app.info)
    assert app.code[0].value == "uv run pitching run"
    assert not list(tmp_path.iterdir())  # Rendering does not generate or download artifacts.


def test_ready_dashboard_filters_pitches_and_held_out_errors(reports):
    app = open_error_view(AppTest.from_file(str(APP), default_timeout=20).run())
    assert not app.exception
    assert metric_values(app)["Pitches"] == "4"
    assert metric_values(app)["Athletes"] == "2"
    assert metric_values(app)["Subset MAE"] == "2.00"
    app.multiselect(key="athlete_filter").select("athlete-a").run()
    assert not app.exception
    values = metric_values(app)
    assert values["Pitches"] == "2"
    assert values["Athletes"] == "1"
    assert values["Subset pitches"] == "2"
    assert values["Subset MAE"] == "1.00"
    error_tables = [table.value for table in app.dataframe if "observed" in table.value.columns]
    assert len(error_tables) == 1
    assert set(error_tables[0]["session_pitch"]) == {"p1", "p2"}
    app.selectbox(key="error_target").select("pitch_speed_mph").run()
    app.selectbox(key="error_model").select("ridge").run()
    assert not app.exception
    error_table = next(table.value for table in app.dataframe if "observed" in table.value.columns)
    assert set(error_table["target"]) == {"pitch_speed_mph"}
    assert set(error_table["model"]) == {"ridge"}
    # Full-CV summary stays complete and is clearly separate from subset metrics.
    full_cv = next(table.value for table in app.dataframe if "n_pitches" in table.value.columns)
    assert full_cv.iloc[0]["n_pitches"] == 4


def test_incompatible_sidebar_filters_show_empty_state(reports):
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    app.radio(key="app_page").set_value("Explore pitches").run()
    app.multiselect(key="athlete_filter").select("athlete-a").run()
    app.multiselect(key="level_filter").select("College").run()
    assert not app.exception
    assert metric_values(app)["Pitches"] == "0"
    assert any("No pitches match both sidebar filters" in item.value for item in app.info)


def test_duplicate_pitch_report_does_not_render_a_multiplying_join(reports):
    frame = pd.read_csv(reports / "analysis.csv")
    pd.concat([frame, frame.iloc[[0]]], ignore_index=True).to_csv(
        reports / "analysis.csv", index=False
    )
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    assert any("one row per nonmissing pitch" in item.value for item in app.error)


def test_interrupted_run_does_not_display_old_model_errors(reports):
    (reports / "run_metadata.json").unlink()
    app = open_error_view(AppTest.from_file(str(APP), default_timeout=20).run())
    assert not app.exception
    assert any("No completed modeling run" in item.value for item in app.info)
    assert "Subset MAE" not in metric_values(app)


def test_changed_artifacts_do_not_display_stale_model_errors(reports):
    predictions = pd.read_csv(reports / "oof_predictions.csv")
    predictions.loc[0, "predicted"] = 123456
    predictions.to_csv(reports / "oof_predictions.csv", index=False)
    app = open_error_view(AppTest.from_file(str(APP), default_timeout=20).run())
    assert not app.exception
    assert any("stale or incomplete" in item.value for item in app.warning)
    assert "Subset MAE" not in metric_values(app)
