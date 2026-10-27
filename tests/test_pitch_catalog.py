"""Expanded recorded-marker coverage stays source-bound and preserves missingness."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pitching.pitch_catalog import (
    ANALYSIS_RELATIVE_PATH,
    catalog_examples,
    load_catalog_frames,
    load_pitch_catalog,
    normalize_catalog_motion,
    prepare_pitch_catalog,
)
from pitching.video_lab import (
    MotionAssetError,
    load_marker_frames,
    load_motion_manifest,
    verified_asset,
)

ROOT = Path(__file__).resolve().parents[1]


def _metadata_copy(tmp_path):
    directory = tmp_path / "assets/pitch_catalog"
    directory.mkdir(parents=True)
    for relative in (
        "source_manifest.json",
        ANALYSIS_RELATIVE_PATH,
        "assets/pitch_catalog/manifest.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    manifest = json.loads((directory / "manifest.json").read_text())
    return directory, manifest


def _write_manifest(directory, manifest):
    (directory / "manifest.json").write_text(json.dumps(manifest, allow_nan=False))


def _synthetic_c3d(labels):
    """Invented numerical fixture used only to test label and missingness behavior."""
    points = np.arange(4 * len(labels) * 4, dtype=float).reshape(4, len(labels), 4)
    return {
        "parameters": {
            "POINT": {
                "LABELS": {"value": labels},
                "UNITS": {"value": ["m"]},
                "RATE": {"value": [360.0]},
            }
        },
        "data": {"points": points, "meta_points": {"residuals": np.zeros((1, len(labels), 4))}},
    }


def test_every_released_pitch_has_a_verified_recording_and_source_missingness_is_retained():
    directory, manifest = load_pitch_catalog(ROOT)
    table = pd.read_csv(ROOT / ANALYSIS_RELATIVE_PATH, dtype={"session_pitch": str, "user": str})
    assert len(manifest["examples"]) == len(table) == 411
    assert manifest["unavailable"] == []
    assert len(catalog_examples(table, manifest)) == len(table)
    counts = []
    for entry in manifest["examples"]:
        arrays = load_catalog_frames(directory, entry)
        assert arrays["positions_m"].dtype == np.float64
        assert arrays["labels"].dtype.kind == "U"
        counts.append(int((~np.isfinite(arrays["positions_m"]).all(axis=2)).sum()))
    assert sum(counts) == manifest["quality_summary"]["n_missing_display_points"] == 11
    assert manifest["quality_summary"]["n_missing_source_points"] == 63
    assert manifest["quality_summary"]["n_athletes_with_recordings"] == 100
    missing = next(entry for entry in manifest["examples"] if entry["session_pitch"] == "1668_3")
    assert missing["missing_points"] == 11
    assert missing["n_source_missing_points"] == 63
    assert manifest["quality_summary"]["prepared_npz_bytes"] < 40 * 1024**2


def test_original_three_recordings_are_numerically_unchanged():
    directory, manifest = load_pitch_catalog(ROOT)
    old_directory, old_manifest = load_motion_manifest(ROOT)
    by_pitch = {entry["session_pitch"]: entry for entry in manifest["examples"]}
    for old in old_manifest["examples"]:
        entry = by_pitch[old["session_pitch"]]
        assert entry["user"] == old["user"]
        assert entry["source_file_sha256"] == old["source_file_sha256"]
        actual = load_catalog_frames(directory, entry)
        expected = load_marker_frames(
            verified_asset(old_directory, old["frames_file"], old["frames_sha256"], ".npz"),
            old["n_frames"],
        )
        for name in ("positions_m", "times_s", "labels", "links"):
            np.testing.assert_array_equal(actual[name], expected[name])


def test_three_namespaced_source_trials_have_explicit_reversible_label_aliases():
    _, manifest = load_pitch_catalog(ROOT)
    entries = [entry for entry in manifest["examples"] if entry["marker_label_aliases"]]
    assert {entry["session_pitch"] for entry in entries} == {"1759_1", "1759_2", "1759_3"}
    assert {entry["user"] for entry in entries} == {"1017"}
    assert manifest["quality_summary"]["n_recordings_with_namespace_aliases"] == 3
    for entry in entries:
        assert len(entry["marker_label_aliases"]) == 48
        assert all(
            raw == "Skeleton_001_" + display
            for raw, display in entry["marker_label_aliases"].items()
        )
        assert set(entry["source_marker_labels"]) == set(entry["marker_label_aliases"])


def test_namespace_cleanup_changes_only_labels_and_retains_invalid_residuals_as_missing():
    c3d = _synthetic_c3d(["Skeleton_001_LSHO", "Skeleton_001_RSHO"])
    c3d["data"]["meta_points"]["residuals"][0, 1, 2] = -1
    before = copy.deepcopy(c3d)
    motion, original, aliases = normalize_catalog_motion(c3d, stride=1)
    assert original == before["parameters"]["POINT"]["LABELS"]["value"]
    assert c3d["parameters"]["POINT"]["LABELS"]["value"] == original
    assert motion["labels"].tolist() == ["LSHO", "RSHO"]
    assert aliases == {"Skeleton_001_LSHO": "LSHO", "Skeleton_001_RSHO": "RSHO"}
    expected = before["data"]["points"][:3].transpose(2, 1, 0).copy()
    expected[2, 1] = np.nan
    np.testing.assert_array_equal(motion["positions_m"], expected)
    np.testing.assert_array_equal(motion["times_s"], np.arange(4) / 360)
    assert motion["missing_points"] == motion["n_source_missing_points"] == 1


@pytest.mark.parametrize(
    "labels",
    [
        ["Skeleton_001_LSHO", "Skeleton_002_RSHO"],
        ["Skeleton_001_LSHO", "RSHO"],
        ["Skeleton_001_LSHO", "Skeleton_001_LSHO"],
        ["Unknown_001_LSHO", "Unknown_001_RSHO"],
    ],
)
def test_ambiguous_colliding_and_unknown_namespaces_are_not_guessed(labels):
    with pytest.raises(ValueError):
        normalize_catalog_motion(_synthetic_c3d(labels), stride=1)


def test_catalog_selection_requires_both_source_pitch_and_athlete():
    _, manifest = load_pitch_catalog(ROOT)
    first, second = manifest["examples"][:2]
    frame = pd.DataFrame(
        {
            "session_pitch": [first["session_pitch"], second["session_pitch"]],
            "user": ["wrong-source-athlete", second["user"]],
        }
    )
    assert catalog_examples(frame, manifest) == [second]
    assert (
        catalog_examples(pd.DataFrame({"session_pitch": [first["session_pitch"]]}), manifest) == []
    )


@pytest.mark.parametrize(
    "alteration",
    [
        "identity",
        "poi",
        "path",
        "count",
        "rate",
        "coverage",
        "quality",
        "alias",
        "bad-id",
        "bad-unit",
    ],
)
def test_catalog_metadata_mismatch_is_rejected(tmp_path, alteration):
    directory, manifest = _metadata_copy(tmp_path)
    first = manifest["examples"][0]
    if alteration == "identity":
        first["user"] = "different-athlete"
    elif alteration == "poi":
        first["poi"]["pitch_speed_mph"] += 1
    elif alteration == "path":
        first["frames_file"] = "../private.npz"
    elif alteration == "count":
        first["n_frames"] += 1
    elif alteration == "rate":
        first["point_rate_hz"] = False
    elif alteration == "coverage":
        manifest["examples"].pop()
    elif alteration == "quality":
        manifest["quality_summary"]["n_available_recordings"] -= 1
    elif alteration == "alias":
        first["marker_label_aliases"] = {first["source_marker_labels"][0]: "invented-joint"}
    elif alteration == "bad-id":
        first["session_pitch"] = {"unexpected": "object"}
    elif alteration == "bad-unit":
        first["units_original"] = {"unexpected": "object"}
    _write_manifest(directory, manifest)
    with pytest.raises(MotionAssetError):
        load_pitch_catalog(tmp_path)


def test_changed_analysis_and_duplicate_json_keys_are_rejected(tmp_path):
    directory, _ = _metadata_copy(tmp_path)
    analysis = tmp_path / ANALYSIS_RELATIVE_PATH
    analysis.write_bytes(analysis.read_bytes() + b"\n")
    with pytest.raises(MotionAssetError, match="different source analysis"):
        load_pitch_catalog(tmp_path)
    (directory / "manifest.json").write_text('{"schema_version": 1, "schema_version": 1}')
    with pytest.raises(MotionAssetError, match="unique-key JSON"):
        load_pitch_catalog(tmp_path)


def test_selected_asset_corruption_and_changed_clock_do_not_render_as_the_recording(tmp_path):
    directory, manifest = load_pitch_catalog(ROOT)
    entry = copy.deepcopy(manifest["examples"][0])
    bad = tmp_path / entry["frames_file"]
    bad.write_bytes(b"corrupted source replay")
    with pytest.raises(MotionAssetError, match="Checksum"):
        load_catalog_frames(tmp_path, entry)
    arrays = load_catalog_frames(directory, entry)
    arrays["times_s"] += 0.001
    np.savez_compressed(bad, **arrays)
    entry["frames_sha256"] = hashlib.sha256(bad.read_bytes()).hexdigest()
    entry["frames_bytes"] = bad.stat().st_size
    with pytest.raises(MotionAssetError, match="source sampling"):
        load_catalog_frames(tmp_path, entry)


def test_preparation_preserves_an_existing_output_directory(tmp_path, monkeypatch):
    directory, _ = _metadata_copy(tmp_path)
    sentinel = directory / "preserve.txt"
    sentinel.write_text("Synthetic test sentinel; preserve operator files")
    before = sentinel.read_bytes()
    monkeypatch.setattr("pitching.pitch_catalog.verify_archive", lambda path: None)
    monkeypatch.setattr(
        "pitching.deployment.verified_demo_reports", lambda root: root / "assets/demo/reports"
    )
    with pytest.raises(ValueError, match="existing catalog"):
        prepare_pitch_catalog(tmp_path, tmp_path / "source.zip", directory)
    assert sentinel.read_bytes() == before


@pytest.mark.parametrize("alteration", ["partial-missing", "complex", "float32"])
def test_rehashed_arrays_must_preserve_the_declared_coordinate_policy(tmp_path, alteration):
    directory, manifest = load_pitch_catalog(ROOT)
    entry = copy.deepcopy(manifest["examples"][0])
    arrays = load_catalog_frames(directory, entry)
    if alteration == "partial-missing":
        arrays["positions_m"][0, 0, 0] = np.nan
    elif alteration == "complex":
        arrays["positions_m"] = arrays["positions_m"].astype(complex)
    else:
        arrays["positions_m"] = arrays["positions_m"].astype(np.float32)
    path = tmp_path / entry["frames_file"]
    np.savez_compressed(path, **arrays)
    entry["frames_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    entry["frames_bytes"] = path.stat().st_size
    with pytest.raises(MotionAssetError):
        load_catalog_frames(tmp_path, entry)


def test_preparation_cli_rejects_an_invalid_archive_without_outputs(tmp_path):
    archive = tmp_path / "pitching_c3d.zip"
    archive.write_bytes(b"An explicitly synthetic invalid archive fixture")
    output = tmp_path / "new-catalog"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/prepare_pitch_catalog.py"),
            "--project-dir",
            str(tmp_path),
            "--archive",
            str(archive),
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "checksum/size mismatch" in result.stderr
    assert not output.exists()
