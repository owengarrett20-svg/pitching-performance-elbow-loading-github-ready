"""Integrity tests for real-source selection and gap-preserving replay preparation."""

import copy
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pitching.data import VARIABLES, join_pitching, read_source
from pitching.motion_examples import (
    exact_archive_member,
    load_motion_manifest,
    normalize_motion,
    select_example_rows,
    sha256_file,
    verify_archive,
)

ROOT = Path(__file__).resolve().parents[1]


def fixture_motion(units="mm"):
    # Deliberately synthetic test-only markers, including a distant fake ball.
    points = np.ones((4, 3, 5))
    points[:3, 0, :] = 1000
    points[:3, 1, :] = 2000
    points[:3, 2, :] = 90000
    residuals = np.zeros((1, 3, 5))
    residuals[0, 0, 2] = -1
    points[1, 1, 4] = np.inf
    return {
        "parameters": {
            "POINT": {
                "LABELS": {"value": ["RSHO", "RELB", "Ball"]},
                "UNITS": {"value": [units]},
                "RATE": {"value": [360.0]},
            }
        },
        "data": {"points": points, "meta_points": {"residuals": residuals}},
    }


def test_motion_units_missing_residuals_and_excluded_ball():
    motion = normalize_motion(fixture_motion(), stride=2)
    np.testing.assert_array_equal(motion["labels"], ["RSHO", "RELB"])
    assert motion["excluded_marker_labels"] == ["Ball"]
    np.testing.assert_allclose(motion["positions_m"][0], [[1, 1, 1], [2, 2, 2]])
    assert np.isnan(motion["positions_m"][1, 0]).all()
    assert np.isnan(motion["positions_m"][2, 1]).all()
    assert motion["missing_points"] == 2
    assert motion["n_source_missing_points"] == 2
    np.testing.assert_allclose(motion["times_s"], np.array([0, 2, 4]) / 360)
    np.testing.assert_array_equal(motion["links"], [[0, 1]])


@pytest.mark.parametrize("units,factor", [("m", 1), ("cm", 0.01), ("mm", 0.001)])
def test_supported_point_units(units, factor):
    motion = normalize_motion(fixture_motion(units), stride=1)
    assert motion["positions_m"][0, 0, 0] == 1000 * factor


@pytest.mark.parametrize("change", ["units", "rate", "residual_shape", "duplicate_labels"])
def test_reject_ambiguous_motion_schema(change):
    c3d = fixture_motion()
    if change == "units":
        c3d["parameters"]["POINT"]["UNITS"]["value"] = ["furlongs"]
    elif change == "rate":
        c3d["parameters"]["POINT"]["RATE"]["value"] = [0]
    elif change == "residual_shape":
        c3d["data"]["meta_points"]["residuals"] = np.zeros((3, 5))
    else:
        c3d["parameters"]["POINT"]["LABELS"]["value"] = ["RSHO", "RSHO", "Ball"]
    with pytest.raises(ValueError):
        normalize_motion(c3d)


def test_selection_is_source_exact_distinct_and_order_independent():
    rows = []
    for pitch, athlete, speed in [
        ("b", "1", 70),
        ("a", "1", 70),
        ("c", "2", 80),
        ("d", "3", 90),
        ("e", "4", np.nan),
    ]:
        rows.append(
            {
                "session_pitch": pitch,
                "user": athlete,
                "filename_new": f"{pitch}.c3d",
                **{column: speed if column == "pitch_speed_mph" else 123.4 for column in VARIABLES},
            }
        )
    analysis = pd.DataFrame(rows)
    selected = select_example_rows(analysis)
    shuffled = select_example_rows(analysis.sample(frac=1, random_state=13))
    assert selected.session_pitch.tolist() == ["a", "c", "d"]
    assert selected.user.nunique() == 3
    pd.testing.assert_frame_equal(selected, shuffled)
    assert selected.max_torso_rotational_velo.tolist() == [123.4] * 3


def test_exact_member_uses_metadata_basename_and_rejects_duplicates(tmp_path):
    path = tmp_path / "synthetic_test_only.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("c3d/123/exact.c3d", b"test fixture")
        archive.writestr("c3d/123/not_exact.c3d", b"test fixture")
    with zipfile.ZipFile(path) as archive:
        assert exact_archive_member(archive, "exact.c3d") == "c3d/123/exact.c3d"
        with pytest.raises(ValueError):
            exact_archive_member(archive, "missing.c3d")
        with pytest.raises(ValueError):
            exact_archive_member(archive, "../exact.c3d")
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("c3d/456/exact.c3d", b"another test fixture")
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError):
        exact_archive_member(archive, "exact.c3d")


def test_reject_changed_archive_before_extracting(tmp_path):
    wrong = tmp_path / "pitching_c3d.zip"
    wrong.write_bytes(b"deliberately invalid test fixture")
    with pytest.raises(ValueError, match="checksum/size"):
        verify_archive(wrong)


@pytest.mark.integration
def test_bundled_recorded_motion_matches_exact_published_poi_and_safe_npz():
    path = ROOT / "assets" / "motion" / "manifest.json"
    if (
        not path.exists()
        or not (ROOT / "data" / "raw" / "baseball_pitching" / "data" / "metadata.csv").exists()
    ):
        pytest.skip("Bundled motion assets or checksum-verified source cache are unavailable.")
    manifest = load_motion_manifest(path)
    poi, metadata = read_source(ROOT / "data" / "raw")
    analysis, _ = join_pitching(poi, metadata)
    selected = select_example_rows(analysis)
    assert selected.session_pitch.tolist() == [
        entry["session_pitch"] for entry in manifest["examples"]
    ]
    for entry in manifest["examples"]:
        row = analysis.set_index("session_pitch").loc[entry["session_pitch"]]
        assert entry["filename_new"] == row.filename_new
        assert entry["user"] == str(row.user)
        for name in VARIABLES:
            assert entry["poi"][name] == float(row[name])
        for file_field, hash_field in [
            ("animation_file", "animation_sha256"),
            ("frames_file", "frames_sha256"),
        ]:
            asset = path.parent / entry[file_field]
            assert asset.is_file()
            assert sha256_file(asset) == entry[hash_field]
        with np.load(path.parent / entry["frames_file"], allow_pickle=False) as frames:
            assert frames["positions_m"].shape == (
                entry["n_frames"],
                len(entry["marker_labels"]),
                3,
            )
            assert frames["labels"].tolist() == entry["marker_labels"]
            assert np.all(np.diff(frames["times_s"]) > 0)
            assert not np.isinf(frames["positions_m"]).any()
            assert frames["links"].max() < len(entry["marker_labels"])


def test_manifest_rejects_unsafe_asset_path(tmp_path):
    source = ROOT / "assets" / "motion" / "manifest.json"
    if not source.exists():
        pytest.skip("Bundled motion manifest unavailable.")
    manifest = copy.deepcopy(load_motion_manifest(source))
    manifest["examples"][0]["frames_file"] = "../private.npz"
    import json

    altered = tmp_path / "manifest.json"
    altered.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="basenames"):
        load_motion_manifest(altered)
