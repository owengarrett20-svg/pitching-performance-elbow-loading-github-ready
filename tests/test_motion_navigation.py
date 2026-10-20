"""A bookmarked replay and consecutive widget changes must show the named pitch."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from pitching.video_lab import load_motion_manifest

ROOT = Path(__file__).resolve().parents[1]


def test_replay_bookmark_and_consecutive_changes_keep_player_and_url_in_agreement():
    _, manifest = load_motion_manifest(ROOT)
    examples = {entry["session_pitch"]: entry for entry in manifest["examples"]}
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
    app.query_params["page"] = "motion"
    app.query_params["pitch"] = "1623_3"
    app.run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.radio(key="app_page").value == "Watch motion"
    app.radio(key="motion_view").set_value("Video & measurement lessons").run()
    assert app.selectbox(key="motion_study_pitch").value["session_pitch"] == "1623_3"
    for identifier in ["2916_4", "1393_3", "1623_3"]:
        app.selectbox(key="motion_study_pitch").set_value(examples[identifier]).run()
        assert not app.exception, [item.value for item in app.exception]
        assert app.selectbox(key="motion_study_pitch").value["session_pitch"] == identifier
        assert app.query_params["pitch"] == identifier
        assert any(
            f"Pitch {identifier} · pseudonymous athlete" in item.value for item in app.caption
        )
