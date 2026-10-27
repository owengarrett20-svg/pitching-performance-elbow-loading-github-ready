"""Comparison bookmarks and table searches must not attach another pitch's motion."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def open_workspace():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
    app.query_params["page"] = "explore"
    app.query_params["pitch"] = "1623_3"
    app.query_params["compare"] = "2916_4"
    app.run()
    assert not app.exception, [item.value for item in app.exception]
    return app


def test_comparison_bookmark_clears_stale_athlete_filters_without_changing_primary():
    app = open_workspace()
    assert app.selectbox(key="workspace_primary_pitch").value == "1623_3"
    assert app.selectbox(key="workspace_compare_pitch").value == "2916_4"
    app.multiselect(key="athlete_filter").set_value(["970"]).run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.selectbox(key="workspace_primary_pitch").value == "1623_3"
    assert app.selectbox(key="workspace_compare_pitch").value != "2916_4"
    app.query_params["compare"] = "2916_4"
    app.run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.multiselect(key="athlete_filter").value == []
    assert app.selectbox(key="workspace_primary_pitch").value == "1623_3"
    assert app.selectbox(key="workspace_compare_pitch").value == "2916_4"
    assert app.query_params["pitch"] == "1623_3"
    assert app.query_params["compare"] == "2916_4"


def test_empty_search_removes_replays_and_clear_restores_actual_source_pair():
    app = open_workspace()
    assert app.get("iframe")
    app.text_input(key="workspace_search").set_value("no such source recording").run()
    assert not app.exception, [item.value for item in app.exception]
    assert not app.get("iframe")
    app.text_input(key="workspace_search").set_value("").run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.get("iframe")
    assert app.selectbox(key="workspace_primary_pitch").value == "1623_3"
    assert app.selectbox(key="workspace_compare_pitch").value == "2916_4"


def test_expanded_source_recording_reaches_dedicated_lab_without_trace_substitution():
    app = open_workspace()
    app.selectbox(key="workspace_primary_pitch").set_value("1759_1").run()
    app.radio(key="app_page").set_value("Watch motion").run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.selectbox(key="lab_motion_pitch").value == "1759_1"
    assert app.query_params["pitch"] == "1759_1"
    assert app.get("iframe")
    assert not any(item.key == "lab_trace_metric" for item in app.selectbox)
    assert any("signals are unavailable" in item.value for item in app.info)
