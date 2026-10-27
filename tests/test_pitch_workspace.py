"""Source selections and searches must never substitute another recorded delivery."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pitching.pitch_workspace import (
    DATA_TERMS,
    WorkspaceSelection,
    _verified_replay,
    comparison_replay_html,
    load_workspace_catalog,
    pitch_from_table_event,
    search_pitch_rows,
    selected_observations_json,
    workspace_table,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def observed():
    """Explicitly synthetic rows for search, missingness, and selection tests only."""
    return pd.DataFrame(
        {
            "session_pitch": ["test-a[1]", "test-a2", "test-b1"],
            "user": ["test-001", "test-001", "test-002"],
            "session": ["test-session-a", "test-session-a", "test-session-b"],
            "playing_level": ["College", "College", "High School"],
            "pitch_speed_mph": [85.3, 84.0, 90.0],
            "elbow_varus_moment": [90.0, np.nan, 120.0],
            "max_shoulder_internal_rotational_velo": [4100.0, 4200.0, 4500.0],
            "max_rotation_hip_shoulder_separation": [21.03, 30.0, 35.0],
            "max_torso_rotational_velo": [1006.1, 1100.0, 1200.0],
        },
        index=[8, 8, 3],
    )


def test_workspace_source_table_is_immutable_and_keeps_missing_values(observed):
    before = observed.copy(deep=True)
    table = workspace_table(observed)
    assert table.session_pitch.tolist() == observed.session_pitch.tolist()
    assert pd.isna(table.loc[1, "elbow_varus_moment"])
    pd.testing.assert_frame_equal(observed, before)
    with pytest.raises(ValueError, match="exactly one"):
        workspace_table(pd.concat([observed, observed.iloc[[0]]]))


def test_literal_search_handles_identity_natural_labels_numbers_and_regex_characters(observed):
    assert search_pitch_rows(observed, "athlete test-001 college").session_pitch.tolist() == [
        "test-a2",
        "test-a[1]",
    ]
    assert search_pitch_rows(observed, "85.3").session_pitch.tolist() == ["test-a[1]"]
    assert search_pitch_rows(observed, "[1]").session_pitch.tolist() == ["test-a[1]"]
    assert search_pitch_rows(observed, ".*").empty
    assert search_pitch_rows(observed, "available").empty
    assert search_pitch_rows(observed, "nan").empty
    assert search_pitch_rows(observed, "HIGH school").session_pitch.tolist() == ["test-b1"]
    assert search_pitch_rows(observed, "session test-session-b").session_pitch.tolist() == [
        "test-b1"
    ]


def test_search_prepares_stable_original_input_row_positions_and_replay_filter(observed):
    table = search_pitch_rows(observed, "", ["test-b1"])
    assert table.session_pitch.tolist() == ["test-b1", "test-a2", "test-a[1]"]
    assert table.index.tolist() == [0, 1, 2]
    assert pitch_from_table_event({"selection": {"rows": [0]}}, table.session_pitch.tolist()) == (
        "test-b1"
    )
    assert search_pitch_rows(
        observed, "", ["test-b1"], replays_only=True
    ).session_pitch.tolist() == ["test-b1"]
    assert search_pitch_rows(observed, "test-001", ["test-b1"], replays_only=True).empty


def test_labeled_identity_search_cannot_match_another_athletes_numeric_measurement(observed):
    observed.loc[observed.user.eq("test-002"), "pitch_speed_mph"] = 970.0
    observed.loc[observed.user.eq("test-001"), "user"] = "970"
    assert set(search_pitch_rows(observed, "athlete 970").user) == {"970"}
    assert set(search_pitch_rows(observed, "athlete:970 college").user) == {"970"}
    assert len(search_pitch_rows(observed, "970")) == 3


@pytest.mark.parametrize(
    "event",
    [
        None,
        [],
        {},
        {"selection": []},
        {"selection": {"rows": []}},
        {"selection": {"rows": [True]}},
        {"selection": {"rows": [1.0]}},
        {"selection": {"rows": [-1]}},
        {"selection": {"rows": [3]}},
        {"selection": {"rows": [0, 1]}},
        {"selection": {"rows": [1, 1]}},
        {"selection": {"rows": "0"}},
    ],
)
def test_invalid_or_stale_table_events_never_select_a_record(event):
    assert pitch_from_table_event(event, ["source-a", "source-b"]) is None


def test_selected_export_preserves_missingness_and_identity_without_json_nan(observed):
    table = workspace_table(observed)
    exported = selected_observations_json(table, WorkspaceSelection("test-a2", "test-b1"))
    payload = json.loads(exported)
    assert payload["observations"][0]["elbow_varus_moment"] is None
    assert payload["observations"][0]["user"] == "test-001"
    assert payload["observations"][1]["session_pitch"] == "test-b1"
    assert payload["source_records"][0]["released_fields"]["session"] == "test-session-a"
    assert payload["source_records"][0]["released_fields"]["elbow_varus_moment"] is None
    assert payload["data_terms"] == DATA_TERMS
    assert "NaN" not in exported


def test_authored_replay_pair_keeps_source_labels_escaped_and_clocks_independent():
    selection = WorkspaceSelection("bad</h2><script>alert(1)</script>", "observed-b")
    document = comparison_replay_html(
        None, None, selection, {"A": '<img src=x onerror="alert(1)">'}
    )
    assert "<script>alert(1)</script>" not in document
    assert "<img src=x" not in document
    assert "&lt;script&gt;" in document
    assert "does not align foot plant" in document
    assert "their own starts" in document
    assert 'src="https://' not in document


def test_corrupt_expanded_catalog_does_not_fall_back_to_legacy_recordings(tmp_path, observed):
    manifest = tmp_path / "assets/pitch_catalog/manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}")
    with pytest.raises(ValueError):
        load_workspace_catalog(tmp_path, observed)


def test_selected_asset_verification_rejects_corruption_labels_and_all_missing(tmp_path):
    arrays = {
        "positions_m": np.zeros((2, 1, 3)),
        "times_s": np.array([0.0, 0.01]),
        "labels": np.array(["RSHO"]),
        "links": np.empty((0, 2), dtype=int),
    }
    path = tmp_path / "test.npz"
    np.savez_compressed(path, **arrays)
    entry = {
        "frames_file": path.name,
        "frames_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "n_frames": 2,
        "marker_labels": ["RSHO"],
    }
    assert _verified_replay(tmp_path, entry)["labels"].tolist() == ["RSHO"]
    with pytest.raises(ValueError, match="labels"):
        _verified_replay(tmp_path, {**entry, "marker_labels": ["different-marker"]})
    path.write_bytes(b"corrupted synthetic test asset")
    with pytest.raises(ValueError, match="Checksum"):
        _verified_replay(tmp_path, entry)
    arrays["positions_m"][:] = np.nan
    np.savez_compressed(path, **arrays)
    entry["frames_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="No complete measured marker"):
        _verified_replay(tmp_path, entry)


def _app():
    script = f"""
from pathlib import Path
import pandas as pd
import streamlit as st
from pitching.pitch_workspace import render_pitch_workspace
root=Path({str(ROOT)!r})
table=pd.read_csv(root/'assets/demo/reports/analysis.csv',dtype={{'session_pitch':str,'user':str}})
result=render_pitch_workspace(table,root,st.session_state.get('parent_primary','1623_3'),st.session_state.get('parent_compare','2916_4'))
if result:
    st.session_state['parent_primary']=result.primary
    st.session_state['parent_compare']=result.comparison
    st.text('actual='+result.primary+'|'+result.comparison)
else:
    st.text('actual=empty')
"""
    return AppTest.from_string(script, default_timeout=30).run()


def test_parent_echo_and_consecutive_dropdown_changes_keep_actual_primary_and_comparison():
    app = _app()
    assert not app.exception, [item.value for item in app.exception]
    assert app.text[-1].value == "actual=1623_3|2916_4"
    for primary in ["1393_3", "2916_4", "1623_3"]:
        app.selectbox(key="workspace_primary_pitch").set_value(primary).run()
        assert not app.exception, [item.value for item in app.exception]
        assert app.selectbox(key="workspace_primary_pitch").value == primary
        assert app.text[-1].value.startswith("actual=" + primary + "|")
    for comparison in ["1393_3", "1623_3", "2916_4"]:
        app.selectbox(key="workspace_compare_pitch").set_value(comparison).run()
        assert app.selectbox(key="workspace_compare_pitch").value == comparison
        assert app.text[-1].value.endswith("|" + comparison)


def test_search_updates_generation_and_empty_results_remove_replays_without_substitution():
    app = _app()
    original_key = next(item.key for item in app.get("dataframe") if item.key)
    app.text_input(key="workspace_search").set_value("athlete 970").run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.text_input(key="workspace_search").value == "athlete 970"
    assert app.selectbox(key="workspace_primary_pitch").value.startswith("1623_")
    new_key = next(item.key for item in app.get("dataframe") if item.key)
    assert new_key != original_key
    app.text_input(key="workspace_search").set_value("NO-SUCH-SOURCE-PITCH").run()
    assert not app.exception
    assert app.text[-1].value == "actual=empty"
    assert not app.get("iframe")
    assert not app.get("video")
    assert any("No pitches match this search" in item.value for item in app.info)


def test_mismatched_athlete_does_not_gain_another_athletes_prepared_replay():
    frame = pd.DataFrame({"session_pitch": ["1623_3"], "user": ["wrong-source-athlete"]})
    _, entries = load_workspace_catalog(ROOT, frame)
    assert "1623_3" not in entries


def test_reused_source_ids_with_changed_observations_do_not_gain_a_released_replay():
    frame = pd.read_csv(
        ROOT / "assets/demo/reports/analysis.csv", dtype={"user": str, "session_pitch": str}
    )
    selected = frame.loc[frame.session_pitch.eq("1623_3")].copy()
    selected["elbow_varus_moment"] += 1
    with pytest.raises(ValueError, match="measurements differ"):
        load_workspace_catalog(ROOT, selected)


def test_source_measurement_mismatch_withholds_optional_movies_as_well_as_marker_replays():
    script = f"""
from pathlib import Path
import pandas as pd
from pitching.pitch_workspace import render_pitch_workspace
root=Path({str(ROOT)!r})
table=pd.read_csv(root/'assets/demo/reports/analysis.csv',dtype={{'session_pitch':str,'user':str}})
table.loc[table.session_pitch.eq('1623_3'),'elbow_varus_moment']+=1
render_pitch_workspace(table,root,'1623_3','2916_4')
"""
    app = AppTest.from_string(script, default_timeout=30).run()
    assert not app.exception, [item.value for item in app.exception]
    assert any("measurements differ" in item.value for item in app.warning)
    assert not app.get("video")
    assert any("No verified matching MP4" in item.value for item in app.info)
