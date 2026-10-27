"""The published demonstration must work without local reports or any network."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_hosted_demo_reads_verified_snapshot_without_fetching_or_fitting(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Hosted demo must not fetch source data or fit models")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("pitching.data.urlopen", forbidden)
    monkeypatch.setattr("pitching.models.evaluate_baselines", forbidden)
    monkeypatch.setattr("pitching.phase2.evaluate_phase2", forbidden)
    monkeypatch.setattr("pitching.phase2.compare_fixed_predictions", forbidden)
    monkeypatch.setenv("PITCHING_REPORT_DIR", str(ROOT / "missing-local-reports"))
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    assert not app.exception, [item.value for item in app.exception]
    assert not app.error, [item.value for item in app.error]
    metrics = {item.label: item.value for item in app.metric}
    assert any("411 recorded pitches · 100 athletes" in item.value for item in app.markdown)
    assert "Subset MAE" not in metrics  # Technical errors are deliberately another route.
    assert len(app.get("video")) == 1
    assert any("Reference demonstration" in item.value for item in app.caption)
    app.radio(key="app_page").set_value("Explore pitches").run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.selectbox(key="workspace_primary_pitch").value
    assert app.selectbox(key="workspace_compare_pitch").value
    app.radio(key="explore_view").set_value("Charts & associations").run()
    assert app.selectbox(key="explorer_pitch").value
    app.radio(key="app_page").set_value("Research brief").run()
    assert not app.exception, [item.value for item in app.exception]
    assert not app.error, [item.value for item in app.error]
    assert len(app.get("download_button")) >= 3
    app.radio(key="app_page").set_value("Watch motion").run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.selectbox(key="lab_motion_pitch").value
    app.radio(key="motion_view").set_value("Video & measurement lessons").run()
    assert len(app.get("video")) == 2
    app.radio(key="app_page").set_value("Athlete reports").run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.selectbox(key="report_athlete").value
    assert len(app.get("download_button")) >= 3
    app.radio(key="app_page").set_value("New-data lab").run()
    assert not app.exception, [item.value for item in app.exception]
    assert any("external study pending" in item.value for item in app.info)
    assert not app.get("file_uploader")
    app.radio(key="app_page").set_value("Study results").run()
    assert not app.exception, [item.value for item in app.exception]
    if (ROOT / "assets/demo/reports/phase2/run_metadata.json").is_file():
        assert app.radio(key="study_story_target").value == "pitch_speed_mph"
        app.radio(key="study_story_target").set_value("elbow_varus_moment").run()
        assert any("remains uncertain" in item.value for item in app.markdown)
        app.radio(key="study_mode").set_value("Detailed audit").run()
        assert app.selectbox(key="phase2_target").value == "pitch_speed_mph"
        assert any("Full-cohort exploratory follow-on" in item.value for item in app.caption)
        assert not any("stale, incomplete, or invalid" in item.value for item in app.warning)
    app.radio(key="study_mode").set_value("Prediction errors").run()
    assert any(metric.label == "Subset MAE" for metric in app.metric)
    app.radio(key="app_page").set_value("Methods & collaboration").run()
    assert not app.exception, [item.value for item in app.exception]
    assert not app.get("file_uploader")
