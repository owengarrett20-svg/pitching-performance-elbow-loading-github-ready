"""Recorded selections must survive changes between the new research views."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def open_bookmark(page, pitch):
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
    app.query_params["page"] = page
    app.query_params["pitch"] = pitch
    app.run()
    assert not app.exception, [item.value for item in app.exception]
    return app


def test_interactive_pitch_changes_and_legacy_mode_keep_actual_recorded_identity():
    app = open_bookmark("motion", "1623_3")
    assert app.selectbox(key="lab_motion_pitch").value == "1623_3"
    for identifier in ["2916_4", "1393_3", "1623_3"]:
        app.selectbox(key="lab_motion_pitch").set_value(identifier).run()
        assert not app.exception, [item.value for item in app.exception]
        assert app.selectbox(key="lab_motion_pitch").value == identifier
        assert app.query_params["pitch"] == identifier
    app.radio(key="motion_view").set_value("Video & measurement lessons").run()
    legacy = app.selectbox(key="motion_study_pitch")
    assert legacy.value["session_pitch"] == "1623_3"
    from pitching.video_lab import load_motion_manifest

    _, manifest = load_motion_manifest(ROOT)
    other = next(entry for entry in manifest["examples"] if entry["session_pitch"] == "1393_3")
    legacy.set_value(other).run()
    app.radio(key="motion_view").set_value("Interactive lab").run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.selectbox(key="lab_motion_pitch").value == "1393_3"
    assert app.query_params["pitch"] == "1393_3"


def test_explorer_report_link_and_consecutive_report_choices_match_shareable_pitch():
    app = open_bookmark("explore", "1623_3")
    action = next(button for button in app.button if button.label == "Create this athlete's report")
    action.click().run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.radio(key="app_page").value == "Athlete reports"
    assert app.selectbox(key="report_athlete").value == "970"
    by_athlete = {"919": "1393", "1596": "2916", "970": "1623"}
    for athlete in ["919", "1596", "970"]:
        app.selectbox(key="report_athlete").set_value(athlete).run()
        assert not app.exception, [item.value for item in app.exception]
        assert app.selectbox(key="report_athlete").value == athlete
        assert app.query_params["pitch"].startswith(by_athlete[athlete] + "_")
    bookmarked = open_bookmark("reports", "2916_4")
    assert bookmarked.selectbox(key="report_athlete").value == "1596"
