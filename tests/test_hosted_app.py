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
    assert metrics["Pitches"] == "411" and metrics["Athletes"] == "100"
    assert "Subset MAE" in metrics
    assert len(app.get("video")) == 2
    assert any("Reference demonstration" in item.value for item in app.caption)
    if (ROOT / "assets/demo/reports/phase2/run_metadata.json").is_file():
        assert app.selectbox(key="phase2_target").value == "pitch_speed_mph"
        assert any("Full-cohort exploratory follow-on" in item.value for item in app.caption)
        assert not any("stale, incomplete, or invalid" in item.value for item in app.warning)
