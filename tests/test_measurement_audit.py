"""Source checks use real public assets; modifications are TEST-ONLY fault fixtures."""

import hashlib
import json
from pathlib import Path
from shutil import copyfile, copytree

import numpy as np
import pandas as pd
import pytest

from pitching.measurement_audit import (
    COLUMNS,
    TOLERANCE,
    audit_measurement_summaries,
    audit_summary,
)
from pitching.trace_examples import SIGNALS

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def analysis():
    return pd.read_csv(
        ROOT / "assets/demo/reports/analysis.csv", dtype={"session_pitch": str, "user": str}
    )


@pytest.fixture
def source_copy(tmp_path):
    """Copy only public source assets; faults in this copy are not research observations."""
    copyfile(ROOT / "source_manifest.json", tmp_path / "source_manifest.json")
    copytree(ROOT / "assets/traces", tmp_path / "assets/traces")
    target = tmp_path / "assets/motion"
    target.mkdir()
    copyfile(ROOT / "assets/motion/manifest.json", target / "manifest.json")
    manifest = json.loads((target / "manifest.json").read_text())
    for entry in manifest["examples"]:
        copyfile(ROOT / "assets/motion" / entry["frames_file"], target / entry["frames_file"])
    return tmp_path


def manifest_at(root):
    return json.loads((root / "assets/traces/manifest.json").read_text())


def write_manifest(root, manifest):
    (root / "assets/traces/manifest.json").write_text(json.dumps(manifest, allow_nan=False))


def modify_trace(root, change):
    manifest = manifest_at(root)
    entry = next(item for item in manifest["examples"] if item["session_pitch"] == "1623_3")
    path = root / "assets/traces" / entry["file"]
    frame = pd.read_csv(path)
    change(frame)
    frame.to_csv(path, index=False)
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_manifest(root, manifest)


def target_row(rows, metric="max_shoulder_internal_rotational_velo"):
    return rows.loc[rows.session_pitch.eq("1623_3") & rows.metric.eq(metric)].iloc[0]


def test_real_twelve_checks_recompute_source_values_offline_without_mutating_inputs(
    analysis, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("The measurement audit must be read-only and offline")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    before = analysis.copy(deep=True)
    rows = audit_measurement_summaries(ROOT, analysis)
    pd.testing.assert_frame_equal(analysis, before)
    assert tuple(rows.columns) == COLUMNS
    assert len(rows) == 12 and rows.status.eq("passed").all()
    assert rows.absolute_difference.le(TOLERANCE).all()
    assert rows.computed_peak.notna().all() and rows.published_poi.notna().all()
    expected_missing = {
        "max_rotation_hip_shoulder_separation": 0,
        "max_shoulder_internal_rotational_velo": 2,
        "max_torso_rotational_velo": 2,
        "elbow_varus_moment": 4,
    }
    assert rows.n_missing.eq(rows.metric.map(expected_missing)).all()
    for field in [name for name in rows if name.endswith("sha256")]:
        assert rows[field].str.fullmatch("[0-9a-f]{64}").all()
    summary = audit_summary(rows)
    assert summary["n_checks"] == summary["n_expected_checks"] == summary["n_passed"] == 12
    assert summary["n_pitches"] == 3 and summary["n_metrics"] == 4
    assert summary["all_passed"] and summary["complete"]
    assert "does not independently validate" in summary["interpretation"]


def test_absent_analysis_pitch_is_unavailable_instead_of_silently_removed(analysis):
    rows = audit_measurement_summaries(ROOT, analysis.loc[~analysis.session_pitch.eq("1623_3")])
    assert len(rows) == 12
    assert rows.loc[rows.session_pitch.eq("1623_3"), "status"].eq("unavailable").all()
    summary = audit_summary(rows)
    assert summary["n_unavailable"] == 4 and summary["n_passed"] == 8
    assert not summary["all_passed"]


def test_wrong_athlete_cannot_pass_or_substitute_another_recording(analysis):
    analysis.loc[analysis.session_pitch.eq("1623_3"), "user"] = "919"
    rows = audit_measurement_summaries(ROOT, analysis)
    bad = rows.loc[rows.session_pitch.eq("1623_3")]
    assert bad.status.eq("failed").all() and bad.computed_peak.isna().all()
    assert bad.detail.str.contains("Athlete identity").all()


@pytest.mark.parametrize(
    "value, status", [(np.nan, "unavailable"), (np.inf, "failed"), (999.0, "failed")]
)
def test_missing_or_inconsistent_analysis_poi_is_never_filled_from_metadata(
    analysis, value, status
):
    metric = "elbow_varus_moment"
    analysis.loc[analysis.session_pitch.eq("1623_3"), metric] = value
    row = target_row(audit_measurement_summaries(ROOT, analysis), metric)
    assert row.status == status and pd.isna(row.computed_peak)
    assert pd.isna(row.absolute_difference)


@pytest.mark.parametrize("fault", ["missing", "corrupt"])
def test_trace_asset_failure_is_four_explicit_unavailable_checks(source_copy, analysis, fault):
    path = source_copy / "assets/traces/1623_3.csv"
    if fault == "missing":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"\n")
    rows = audit_measurement_summaries(source_copy, analysis)
    bad = rows.loc[rows.session_pitch.eq("1623_3")]
    assert bad.status.eq("unavailable").all() and bad.computed_peak.isna().all()
    assert audit_summary(rows)["n_passed"] == 8


def test_motion_asset_integrity_is_required_for_the_identity_link(source_copy, analysis):
    path = source_copy / "assets/motion/1623_3.npz"
    path.write_bytes(b"TEST-ONLY corrupted public marker asset")
    rows = audit_measurement_summaries(source_copy, analysis)
    assert rows.loc[rows.session_pitch.eq("1623_3"), "status"].eq("unavailable").all()
    assert not audit_summary(rows)["all_passed"]


def test_native_negative_magnitude_is_not_mislabeled_as_positive_peak(source_copy, analysis):
    signal = SIGNALS["max_shoulder_internal_rotational_velo"]

    def change(frame):
        for name in (signal["raw_column"], signal["column"]):
            frame.loc[0, name] = -99999.0

    modify_trace(source_copy, change)
    rows = audit_measurement_summaries(source_copy, analysis)
    row = target_row(rows)
    assert row.status == "passed"
    assert row.computed_peak == pytest.approx(row.published_poi, abs=TOLERANCE)
    assert row.computed_peak < 99999


def test_recomputed_peak_detects_value_change_despite_rehashed_asset(source_copy, analysis):
    signal = SIGNALS["max_shoulder_internal_rotational_velo"]

    def change(frame):
        for name in (signal["raw_column"], signal["column"]):
            frame.loc[frame[name].idxmax(), name] += 1.0

    modify_trace(source_copy, change)
    row = target_row(audit_measurement_summaries(source_copy, analysis))
    assert row.status == "failed"
    assert row.absolute_difference == pytest.approx(1.0)


def test_display_alias_sign_flip_is_failed_even_if_its_own_maximum_looks_plausible(
    source_copy, analysis
):
    column = SIGNALS["max_shoulder_internal_rotational_velo"]["column"]
    modify_trace(source_copy, lambda frame: frame.__setitem__(column, -frame[column]))
    row = target_row(audit_measurement_summaries(source_copy, analysis))
    assert row.status == "failed" and "native signal sign" in row.detail


def test_all_missing_trace_values_remain_unavailable_and_are_counted(source_copy, analysis):
    signal = SIGNALS["max_shoulder_internal_rotational_velo"]

    def change(frame):
        frame[signal["raw_column"]] = np.nan
        frame[signal["column"]] = np.nan

    modify_trace(source_copy, change)
    row = target_row(audit_measurement_summaries(source_copy, analysis))
    assert row.status == "unavailable" and pd.isna(row.computed_peak)
    assert row.n_missing == row.n_samples == 806


def test_infinite_signal_is_failed_instead_of_verified_as_a_finite_measurement(
    source_copy, analysis
):
    signal = SIGNALS["max_shoulder_internal_rotational_velo"]

    def change(frame):
        frame.loc[0, signal["raw_column"]] = np.inf
        frame.loc[0, signal["column"]] = np.inf

    modify_trace(source_copy, change)
    row = target_row(audit_measurement_summaries(source_copy, analysis))
    assert row.status == "failed" and "Infinite" in row.detail


@pytest.mark.parametrize(
    "field,value", [("unit", "rad/s"), ("sign", -1), ("source_column", "other")]
)
def test_comparison_semantics_must_match_reviewed_signal_mapping(
    source_copy, analysis, field, value
):
    manifest = manifest_at(source_copy)
    entry = next(item for item in manifest["examples"] if item["session_pitch"] == "1623_3")
    comparison = next(
        item
        for item in entry["comparison"]
        if item["metric"] == "max_shoulder_internal_rotational_velo"
    )
    comparison[field] = value
    write_manifest(source_copy, manifest)
    row = target_row(audit_measurement_summaries(source_copy, analysis))
    assert row.status == "failed" and "inconsistent" in row.detail


def test_cached_previous_trace_max_is_not_used_as_computed_evidence(source_copy, analysis):
    manifest = manifest_at(source_copy)
    for entry in manifest["examples"]:
        for comparison in entry["comparison"]:
            comparison["trace_max"] = -123456.0  # TEST-ONLY stale cached rendering.
    write_manifest(source_copy, manifest)
    rows = audit_measurement_summaries(source_copy, analysis)
    assert audit_summary(rows)["all_passed"]


@pytest.mark.parametrize("fault", ["duplicate_id", "missing_id", "missing_column"])
def test_structurally_invalid_analysis_is_rejected(analysis, fault):
    if fault == "duplicate_id":
        analysis = pd.concat([analysis, analysis.iloc[[0]]], ignore_index=True)
    elif fault == "missing_id":
        analysis.loc[0, "user"] = None
    else:
        analysis = analysis.drop(columns="elbow_varus_moment")
    with pytest.raises(ValueError):
        audit_measurement_summaries(ROOT, analysis)


@pytest.mark.parametrize("fault", ["repeated_pitch", "source_revision", "signal_definition"])
def test_unreviewed_manifest_structure_or_signal_definitions_are_rejected(
    source_copy, analysis, fault
):
    manifest = manifest_at(source_copy)
    if fault == "repeated_pitch":
        manifest["examples"][1] = manifest["examples"][0]
    elif fault == "source_revision":
        manifest["source_commit"] = "unreviewed"
    else:
        manifest["signals"]["elbow_varus_moment"]["unit"] = "N"
    write_manifest(source_copy, manifest)
    with pytest.raises(ValueError):
        audit_measurement_summaries(source_copy, analysis)


def test_partial_empty_or_duplicated_tables_cannot_claim_all_reviewed_checks_pass(analysis):
    rows = audit_measurement_summaries(ROOT, analysis)
    assert not audit_summary(rows.iloc[:1])["all_passed"]
    assert not audit_summary(rows.iloc[:0])["all_passed"]
    assert audit_summary(rows.iloc[:0])["n_passed"] == 0
    with pytest.raises(ValueError, match="repeated"):
        audit_summary(pd.concat([rows, rows.iloc[[0]]]))
    rows.loc[0, "status"] = "verified injury safety"
    with pytest.raises(ValueError, match="unknown"):
        audit_summary(rows)
