"""Viewer checks use explicitly synthetic test assets, never invented research records."""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pitching.video_lab import (
    SOURCE_COMMIT,
    MotionAssetError,
    load_marker_frames,
    load_motion_manifest,
    matching_examples,
    verified_asset,
)


@pytest.fixture
def motion_assets(tmp_path):
    """Tiny synthetic arrays and non-codec bytes exercise paths, not biomechanics or decoding."""
    directory = tmp_path / "assets" / "motion"
    directory.mkdir(parents=True)
    positions = np.zeros((3, 3, 3), dtype=float)
    positions[1, 1] = np.nan  # Preserve missing marker coordinates without interpolation.
    np.savez_compressed(
        directory / "synthetic.npz",
        positions_m=positions,
        times_s=np.array([0.0, 0.01, 0.02]),
        labels=np.array(["test-a", "test-b", "test-c"]),
        links=np.array([[0, 1], [1, 2]], dtype=int),
    )
    (directory / "synthetic.mp4").write_bytes(b"explicitly synthetic media test bytes")
    example = {
        "session_pitch": "synthetic-pitch",
        "user": "synthetic-athlete",
        "filename_new": "synthetic-c3d.c3d",
        "animation_file": "synthetic.mp4",
        "animation_sha256": hashlib.sha256((directory / "synthetic.mp4").read_bytes()).hexdigest(),
        "frames_file": "synthetic.npz",
        "frames_sha256": hashlib.sha256((directory / "synthetic.npz").read_bytes()).hexdigest(),
        "point_rate_hz": 100.0,
        "n_source_frames": 3,
        "n_frames": 3,
        "playback_rate": 0.25,
        "poi": {"pitch_speed_mph": 80.0},
    }
    (directory / "manifest.json").write_text(
        json.dumps({"schema_version": 1, "source_commit": SOURCE_COMMIT, "examples": [example]})
    )
    return tmp_path, directory, example


def viewer_app(project_root, *, user="synthetic-athlete", pitch="synthetic-pitch"):
    source = f"""
from pathlib import Path
import pandas as pd
import streamlit as st
from pitching.video_lab import render_video_lab
selected = render_video_lab(
    pd.DataFrame({{'session_pitch': [{pitch!r}], 'user': [{user!r}]}}),
    Path({str(project_root)!r}),
)
st.text('selected=' + str(selected))
"""
    return AppTest.from_string(source, default_timeout=20).run()


def test_missing_motion_assets_does_not_break_teaching_tab(tmp_path):
    app = viewer_app(tmp_path)
    assert not app.exception
    assert any("not available locally" in item.value for item in app.info)
    assert app.text[0].value == "selected=None"
    assert app.checkbox(key="motion_load_camera").value is False
    assert not list(tmp_path.iterdir())  # A rerun never fetches or generates assets.


def test_selected_pitch_requires_matching_athlete_and_pitch(motion_assets):
    root, _, example = motion_assets
    good = pd.DataFrame({"session_pitch": [example["session_pitch"]], "user": [example["user"]]})
    assert matching_examples(good, [example]) == [example]
    bad = good.assign(user="another-athlete")
    assert matching_examples(bad, [example]) == []
    app = viewer_app(root, user="another-athlete")
    assert not app.exception
    assert any("None matches both pitch and athlete" in item.value for item in app.info)
    assert app.text[0].value == "selected=None"
    assert not any(item.key == "motion_study_pitch" for item in app.selectbox)


def test_valid_local_assets_render_and_preserve_missing_markers(motion_assets):
    root, directory, example = motion_assets
    app = viewer_app(root)
    assert not app.exception
    assert app.text[0].value == "selected=synthetic-pitch"
    assert "80.0 mph" in app.selectbox(key="motion_study_pitch").options[0]
    assert app.checkbox(key="motion_load_camera").value is False
    arrays = load_marker_frames(directory / example["frames_file"], 3)
    assert np.isnan(arrays["positions_m"][1, 1]).all()
    app.checkbox(key="motion_inspect").check().run()
    assert not app.exception
    app.slider(key="motion_frame_synthetic-pitch").set_value(1).run()
    assert not app.exception


def test_asset_checksum_failure_blocks_media_display(motion_assets):
    root, directory, _ = motion_assets
    (directory / "synthetic.mp4").write_bytes(b"changed bytes")
    app = viewer_app(root)
    assert not app.exception
    assert any("Checksum mismatch" in item.value for item in app.warning)
    assert app.text[0].value == "selected=None"
    assert not any(item.key == "motion_inspect" for item in app.checkbox)


@pytest.mark.parametrize(
    "filename", ["../elsewhere.mp4", "/tmp/elsewhere.mp4", "..\\elsewhere.mp4"]
)
def test_asset_basename_cannot_escape_directory(motion_assets, filename):
    _, directory, _ = motion_assets
    with pytest.raises(MotionAssetError, match="basename"):
        verified_asset(directory, filename, "a" * 64, ".mp4")


def test_asset_symlink_cannot_escape_directory(motion_assets):
    root, directory, _ = motion_assets
    outside = root / "outside.mp4"
    outside.write_bytes(b"outside")
    (directory / "escape.mp4").symlink_to(outside)
    with pytest.raises(MotionAssetError, match="outside"):
        verified_asset(directory, "escape.mp4", hashlib.sha256(b"outside").hexdigest(), ".mp4")


def test_unpinned_or_duplicate_motion_manifests_are_rejected(motion_assets):
    root, directory, example = motion_assets
    manifest = directory / "manifest.json"
    manifest.write_text(json.dumps({"schema": 1, "source_commit": "wrong", "examples": [example]}))
    with pytest.raises(MotionAssetError, match="pinned"):
        load_motion_manifest(root)
    manifest.write_text(
        json.dumps({"schema": 1, "source_commit": SOURCE_COMMIT, "examples": [example, example]})
    )
    with pytest.raises(MotionAssetError, match="duplicate"):
        load_motion_manifest(root)


def test_marker_archive_rejects_pickle_objects_and_bad_links(tmp_path):
    path = tmp_path / "unsafe.npz"
    np.savez(
        path,
        positions_m=np.zeros((2, 2, 3)),
        times_s=np.array([0.0, 0.1]),
        labels=np.array([object(), object()], dtype=object),
        links=np.array([[0, 1]]),
    )
    with pytest.raises(MotionAssetError, match="unsafe"):
        load_marker_frames(path)
    np.savez(
        path,
        positions_m=np.zeros((2, 2, 3)),
        times_s=np.array([0.0, 0.1]),
        labels=np.array(["a", "b"]),
        links=np.array([[0, 2]]),
    )
    with pytest.raises(MotionAssetError, match="indices"):
        load_marker_frames(path)


def test_marker_archive_rejects_nonincreasing_times(motion_assets):
    _, directory, _ = motion_assets
    arrays = load_marker_frames(directory / "synthetic.npz")
    arrays["times_s"][1] = arrays["times_s"][0]
    path = directory / "bad-times.npz"
    np.savez(path, **arrays)
    with pytest.raises(MotionAssetError, match="strictly increasing"):
        load_marker_frames(path)
