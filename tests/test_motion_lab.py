"""The marker lab preserves observed samples, eligible IDs, and clock boundaries."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pitching.motion_lab import (
    clock_audit,
    marker_coordinate_table,
    marker_regions,
    marker_viewer_html,
    viewer_payload,
)
from pitching.trace_examples import SIGNALS
from pitching.trace_viewer import interval_peak, load_trace_example
from pitching.video_lab import load_marker_frames, load_motion_manifest, verified_asset

ROOT = Path(__file__).resolve().parents[1]


def _arrays():
    return {
        "positions_m": np.array(
            [
                [[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]],
                [[0.5, 0.0, 0.0], [np.nan, np.nan, np.nan]],
            ]
        ),
        "times_s": np.array([0.0, 0.01]),
        "labels": np.array(["C7", "RSHO"]),
        "links": np.array([[0, 1]]),
    }


def _entry():
    return {
        "session_pitch": "synthetic",
        "user": "synthetic-athlete",
        "point_rate_hz": 100.0,
        "n_source_frames": 2,
    }


def test_json_payload_keeps_missing_markers_and_world_coordinates():
    payload = viewer_payload(_arrays(), _entry())
    assert payload["positions"][0][1] == [1.0, 2.0, 3.0]
    assert payload["positions"][1][1] == [None, None, None]
    assert payload["times"] == [0.0, 0.01]
    assert payload["links"] == [[0, 1]]
    assert "NaN" not in json.dumps(payload, allow_nan=False)
    table = marker_coordinate_table(_arrays(), 1)
    assert not table.loc[1, "Complete coordinates"]
    assert pd.isna(table.loc[1, "X (m)"])
    with pytest.raises(ValueError, match="outside"):
        marker_coordinate_table(_arrays(), 2)


def test_marker_groups_use_known_labels_and_do_not_drop_other_observations():
    result = marker_regions(["C7", "RSHO", "LTOE", "unclassified", "LFHD"])
    assert result["All markers"] == [0, 1, 2, 3, 4]
    assert result["Head"] == [4]
    assert result["Trunk"] == [0]
    assert result["Upper limbs"] == [1]
    assert result["Lower limbs"] == [2]


def test_equal_grids_do_not_establish_a_shared_clock():
    trace = pd.DataFrame({"time": [0.0, 0.01]})
    audit = clock_audit(_arrays(), trace, _entry())
    assert audit["trace_matches_zero_based_source_grid"]
    assert audit["status"] == "unverified"
    shifted = clock_audit(_arrays(), trace.assign(time=[0.1, 0.11]), _entry())
    assert not shifted["trace_matches_zero_based_source_grid"]
    assert shifted["status"] == "unverified"
    for time in [[0.0, np.inf], [0.0, 0.0], [0.1, 0.0]]:
        with pytest.raises(ValueError, match="time grid"):
            clock_audit(_arrays(), trace.assign(time=time), _entry())
    for rate in [0, -1, np.inf, np.nan]:
        with pytest.raises(ValueError, match="sample rate"):
            clock_audit(_arrays(), trace, _entry() | {"point_rate_hz": rate})


def test_all_missing_marker_sample_remains_a_missing_sample_with_finite_display_bounds():
    arrays = _arrays()
    arrays["positions_m"][:] = np.nan
    payload = viewer_payload(arrays, _entry())
    assert payload["center"] == [0.0, 0.0, 0.0]
    assert payload["radius"] == 1.0
    assert payload["positions"] == [[[None, None, None]] * 2] * 2
    assert "NaN" not in json.dumps(payload, allow_nan=False)


def test_standalone_viewer_escapes_script_and_html_boundaries():
    arrays = _arrays()
    arrays["labels"] = np.array(["C7", "</script><img src=x onerror=alert(1)>"])
    entry = _entry() | {"user": "<img src=x onerror=alert(2)>"}
    document = marker_viewer_html(arrays, entry)
    assert document.count("<script>") == document.count("</script>") == 1
    assert "<img" not in document
    assert "\\u003c/script\\u003e" in document
    assert "&lt;img" in document
    assert 'aria-label="Marker replay frame"' in document
    assert 'aria-label="Highlight marker region"' in document
    assert "Marker–signal timing is not verified" in document
    assert "requestAnimationFrame" in document
    assert "<script src=" not in document
    assert "fetch(" not in document


def _lab_app(requested="1623_3"):
    return AppTest.from_string(
        f"""
from pathlib import Path
import pandas as pd
import streamlit as st
from pitching.motion_lab import render_motion_lab
root=Path({str(ROOT)!r})
frame=pd.read_csv(root/'assets/demo/reports/analysis.csv', dtype={{'session_pitch':'string','user':'string'}})
if 'active' not in st.session_state:st.session_state.active={requested!r}
chosen=render_motion_lab(frame,root,st.session_state.active)
st.session_state.active=chosen
st.text('selected='+str(chosen))
""",
        default_timeout=30,
    ).run()


def test_prepared_marker_replays_and_trace_peaks_are_source_bound():
    directory, manifest = load_motion_manifest(ROOT)
    for entry in manifest["examples"]:
        arrays = load_marker_frames(
            verified_asset(directory, entry["frames_file"], entry["frames_sha256"], ".npz"),
            entry["n_frames"],
        )
        payload = viewer_payload(arrays, entry)
        assert len(payload["positions"]) == entry["n_frames"]
        trace, trace_entry, _ = load_trace_example(ROOT, entry["session_pitch"])
        assert str(trace_entry["user"]) == entry["user"]
        assert clock_audit(arrays, trace, entry)["status"] == "unverified"
        for comparison in trace_entry["comparison"]:
            peak = interval_peak(
                trace, SIGNALS[comparison["metric"]]["column"], trace.time.min(), trace.time.max()
            )
            assert peak["peak"] == pytest.approx(comparison["published_poi"], abs=1e-4)


def test_bookmark_and_consecutive_changes_keep_actual_recording_selected():
    app = _lab_app()
    assert not app.exception, [item.value for item in app.exception]
    assert app.selectbox(key="lab_motion_pitch").value == "1623_3"
    for identifier in ["2916_4", "1393_3", "1623_3", "1393_3"]:
        app.selectbox(key="lab_motion_pitch").set_value(identifier).run()
        assert not app.exception, [item.value for item in app.exception]
        assert app.selectbox(key="lab_motion_pitch").value == identifier
        assert app.text[-1].value == f"selected={identifier}"
    assert any("timing is not verified" in item.value for item in app.info)


def test_trace_peak_jump_uses_trace_index_and_preserves_marker_clock_boundary():
    app = _lab_app()
    app.selectbox(key="lab_trace_metric").set_value("elbow_varus_moment").run()
    app.button(key="lab_trace_peak").click().run()
    assert not app.exception, [item.value for item in app.exception]
    frame, _, _ = load_trace_example(ROOT, "1623_3")
    expected = int(frame.elbow_varus_moment_nm.idxmax())
    assert app.slider(key="lab_trace_sample_1623_3").value == expected
    assert app.slider(key="lab_marker_table_1623_3").value == 0
    app.slider(key="lab_marker_table_1623_3").set_value(1).run()
    assert app.slider(key="lab_trace_sample_1623_3").value == expected


def test_unavailable_pitch_explains_actual_replay_and_mismatched_athlete_is_not_substituted():
    app = _lab_app("not-an-example")
    assert not app.exception
    assert any("no prepared recording" in item.value for item in app.info)
    source = f"""
from pathlib import Path
import pandas as pd
import streamlit as st
from pitching.motion_lab import render_motion_lab
result=render_motion_lab(pd.DataFrame({{'session_pitch':['1623_3'],'user':['wrong-athlete']}}),Path({str(ROOT)!r}))
st.text('selected='+str(result))
"""
    filtered = AppTest.from_string(source, default_timeout=20).run()
    assert not filtered.exception
    assert filtered.text[-1].value == "selected=None"
    assert not any(item.key == "lab_motion_pitch" for item in filtered.selectbox)


def test_corrupted_marker_asset_is_not_rendered_or_replaced_by_another_pitch(tmp_path):
    directory, manifest = load_motion_manifest(ROOT)
    local = tmp_path / "assets/motion"
    local.mkdir(parents=True)
    (local / "manifest.json").write_text(json.dumps(manifest))
    entry = next(item for item in manifest["examples"] if item["session_pitch"] == "1623_3")
    assert (directory / entry["frames_file"]).is_file()
    (local / entry["frames_file"]).write_bytes(b"corrupted test asset")
    source = f"""
from pathlib import Path
import pandas as pd
import streamlit as st
from pitching.motion_lab import render_motion_lab
frame=pd.read_csv(Path({str(ROOT)!r})/'assets/demo/reports/analysis.csv',dtype={{'session_pitch':'string','user':'string'}})
result=render_motion_lab(frame,Path({str(tmp_path)!r}),'1623_3')
st.text('selected='+str(result))
"""
    app = AppTest.from_string(source, default_timeout=20).run()
    assert not app.exception
    assert app.text[-1].value == "selected=None"
    assert any("Checksum mismatch" in item.value for item in app.warning)
    assert not app.get("iframe")
