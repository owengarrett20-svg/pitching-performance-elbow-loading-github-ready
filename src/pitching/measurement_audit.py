"""Reproduce released scalar summaries from the three prepared source traces.

This is a source-consistency check. It neither reconstructs joint kinematics or
inverse dynamics nor establishes independent measurement validity or shared clocks.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from pitching.data import COMMIT
from pitching.trace_examples import EXAMPLE_IDS, SIGNALS
from pitching.trace_viewer import load_trace_example
from pitching.video_lab import load_motion_manifest, verified_asset

TOLERANCE = 1e-4
SCOPE = "source_scalar_reproduction_only"
INTERPRETATION = (
    "Agreement reproduces scalar summaries from released processed signals in three selected "
    "examples. It does not independently validate anatomical coordinates, filtering, original "
    "POI windows, inverse dynamics, tissue loading, or marker/signal clock alignment."
)
COLUMNS = (
    "session_pitch",
    "user",
    "metric",
    "label",
    "unit",
    "source_column",
    "display_column",
    "sign",
    "n_samples",
    "n_missing",
    "computed_peak",
    "peak_time",
    "published_poi",
    "absolute_difference",
    "tolerance",
    "status",
    "detail",
    "source_commit",
    "analysis_input_sha256",
    "source_manifest_sha256",
    "trace_manifest_sha256",
    "motion_manifest_sha256",
    "trace_sha256",
    "motion_frames_sha256",
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_manifest(path: Path) -> tuple[dict, str]:
    def unique(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise ValueError(f"Duplicate JSON key in {path.name}")
            result[name] = value
        return result

    payload = path.read_bytes()
    value = json.loads(payload, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")  # noqa: TRY004 - serialized content
    return value, _sha(payload)


def _analysis_table(analysis: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    columns = ["session_pitch", "user", *SIGNALS]
    missing = set(columns) - set(analysis)
    if missing:
        raise ValueError(f"Measurement audit needs columns: {', '.join(sorted(missing))}")
    table = analysis[columns].copy()
    for name in ("session_pitch", "user"):
        if table[name].isna().any():
            raise ValueError("Measurement audit identifiers cannot be missing")
        table[name] = table[name].astype(str)
        if table[name].str.strip().eq("").any():
            raise ValueError("Measurement audit identifiers cannot be empty")
    if table.session_pitch.duplicated().any():
        raise ValueError("Measurement audit requires one row per pitch")
    for name in SIGNALS:
        table[name] = pd.to_numeric(table[name], errors="raise").astype(float)
    table = table.sort_values("session_pitch").reset_index(drop=True)
    payload = table.to_csv(index=False, float_format="%.17g", lineterminator="\n").encode()
    return table.set_index("session_pitch"), _sha(payload)


def _trace_manifest(root: Path) -> tuple[dict, str]:
    manifest, digest = _read_manifest(root / "assets/traces/manifest.json")
    if manifest.get("schema_version") != 1 or manifest.get("source_commit") != COMMIT:
        raise ValueError("Trace manifest differs from the reviewed source revision/schema")
    if manifest.get("signals") != SIGNALS:
        raise ValueError("Trace signal definitions, units, or signs differ from reviewed mappings")
    entries = manifest.get("examples")
    if not isinstance(entries, list) or not all(isinstance(item, dict) for item in entries):
        raise ValueError("Trace manifest has no valid example list")
    ids = [item.get("session_pitch") for item in entries]
    if len(ids) != len(EXAMPLE_IDS) or set(ids) != set(EXAMPLE_IDS):
        raise ValueError("Trace manifest must contain each of the three reviewed pitch IDs once")
    for entry in entries:
        pitch = entry["session_pitch"]
        if entry.get("file") != f"{pitch}.csv" or not isinstance(entry.get("user"), str):
            raise ValueError("Trace manifest has inconsistent source identity or local filename")
    return manifest, digest


def _comparisons(entry: dict) -> dict[str, dict]:
    comparisons = entry.get("comparison")
    if not isinstance(comparisons, list) or not all(isinstance(item, dict) for item in comparisons):
        raise ValueError("Trace has no valid source comparisons")
    names = [item.get("metric") for item in comparisons]
    if len(names) != len(SIGNALS) or set(names) != set(SIGNALS):
        raise ValueError("Trace must declare each reviewed scalar comparison once")
    return {item["metric"]: item for item in comparisons}


def audit_measurement_summaries(project_root: Path, analysis: pd.DataFrame) -> pd.DataFrame:
    """Check each released trace maximum against the actual analysis-table POI.

    Invalid structural manifests/analysis tables raise an error. A missing or
    corrupted per-pitch asset yields four explicitly unavailable checks instead
    of silently dropping that example. Identity and numerical inconsistencies
    are failed checks. Input tables and source files remain unchanged.
    """
    root = Path(project_root)
    table, analysis_digest = _analysis_table(analysis)
    source, source_digest = _read_manifest(root / "source_manifest.json")
    if source.get("commit") != COMMIT:
        raise ValueError("Source manifest differs from the reviewed revision")
    manifest, trace_manifest_digest = _trace_manifest(root)
    motion_dir, motion = load_motion_manifest(root)
    _, motion_digest = _read_manifest(motion_dir / "manifest.json")
    motions = {entry["session_pitch"]: entry for entry in motion["examples"]}
    if not set(EXAMPLE_IDS).issubset(motions):
        raise ValueError("Motion manifest lacks a reviewed trace's pitch identity")
    rows = []
    for entry in manifest["examples"]:
        pitch, athlete = entry["session_pitch"], entry["user"]
        base = {
            "session_pitch": pitch,
            "user": athlete,
            "source_commit": COMMIT,
            "analysis_input_sha256": analysis_digest,
            "source_manifest_sha256": source_digest,
            "trace_manifest_sha256": trace_manifest_digest,
            "motion_manifest_sha256": motion_digest,
            "trace_sha256": entry.get("sha256"),
            "motion_frames_sha256": motions[pitch].get("frames_sha256"),
        }
        problem, state, frame, comparisons = None, "unavailable", None, {}
        if pitch not in table.index:
            problem = "The input analysis table has no matching recorded pitch."
        elif table.loc[pitch, "user"] != athlete or motions[pitch]["user"] != athlete:
            problem, state = "Athlete identity differs between source records.", "failed"
        else:
            try:
                frame, loaded_entry, _ = load_trace_example(root, pitch)
                if loaded_entry != entry:
                    raise ValueError("Trace manifest changed while the audit was reading it")
                if type(entry.get("n_samples")) is not int or len(frame) != entry["n_samples"]:
                    raise ValueError("Trace sample count differs from its declared coverage")
                if not np.isfinite(pd.to_numeric(frame.time, errors="raise")).all():
                    raise ValueError("Trace time coordinates must be finite")
                verified_asset(
                    motion_dir,
                    motions[pitch]["frames_file"],
                    motions[pitch]["frames_sha256"],
                    ".npz",
                )
                comparisons = _comparisons(entry)
            except (OSError, ValueError, KeyError, TypeError) as error:
                problem = str(error)
        for metric, signal in SIGNALS.items():
            row = {
                **base,
                "metric": metric,
                "label": signal["label"],
                "unit": signal["unit"],
                "source_column": signal["raw_column"],
                "display_column": signal["column"],
                "sign": signal["sign"],
                "n_samples": None,
                "n_missing": None,
                "computed_peak": None,
                "peak_time": None,
                "published_poi": None,
                "absolute_difference": None,
                "tolerance": TOLERANCE,
                "status": state,
                "detail": problem,
            }
            if problem is not None:
                rows.append(row)
                continue
            try:
                comparison = comparisons[metric]
                for name, expected in (
                    ("source_column", signal["raw_column"]),
                    ("display_column", signal["column"]),
                    ("unit", signal["unit"]),
                    ("sign", signal["sign"]),
                ):
                    if comparison.get(name) != expected:
                        raise ValueError("Source comparison column, unit, or sign is inconsistent")
                poi = float(table.loc[pitch, metric])
                if np.isnan(poi):
                    row["detail"] = "Published analysis-table value is missing; no value is filled."
                    rows.append(row)
                    continue
                if not np.isfinite(poi):
                    raise ValueError("Published analysis-table value is nonfinite")
                row["published_poi"] = poi
                if (
                    float(comparison["published_poi"]) != poi
                    or float(motions[pitch]["poi"][metric]) != poi
                ):
                    raise ValueError(
                        "Published POI differs between analysis, trace, and motion metadata"
                    )
                native = pd.to_numeric(frame[signal["raw_column"]], errors="raise").to_numpy(float)
                displayed = pd.to_numeric(frame[signal["column"]], errors="raise").to_numpy(float)
                row["n_samples"] = len(displayed)
                row["n_missing"] = int((~np.isfinite(displayed)).sum())
                if not np.array_equal(displayed, signal["sign"] * native, equal_nan=True):
                    raise ValueError(
                        "Display alias does not preserve the reviewed native signal sign"
                    )
                if np.isinf(displayed).any():
                    raise ValueError(
                        "Infinite signal values cannot be verified source measurements"
                    )
                finite = np.isfinite(displayed)
                if not finite.any():
                    row["detail"] = "No finite released signal samples; no peak is invented."
                    rows.append(row)
                    continue
                peak = float(displayed[finite].max())
                index = int(np.flatnonzero(finite & (displayed == peak))[0])
                difference = abs(peak - poi)
                row.update(
                    computed_peak=peak,
                    peak_time=float(frame.time.iloc[index]),
                    absolute_difference=difference,
                    status="passed" if difference <= TOLERANCE else "failed",
                    detail="Maximum finite signed sample over the complete released trace.",
                )
            except (ValueError, KeyError, TypeError) as error:
                row.update(status="failed", detail=str(error))
            rows.append(row)
    return pd.DataFrame(rows, columns=COLUMNS)


def audit_summary(rows: pd.DataFrame) -> dict:
    """Count explicit results; a partial or empty table never becomes a full pass."""
    required = {"session_pitch", "metric", "status"}
    if not required.issubset(rows):
        raise ValueError("Measurement audit table is missing identifier or status columns")
    if rows.duplicated(["session_pitch", "metric"]).any():
        raise ValueError("Measurement audit has repeated pitch/metric checks")
    if not rows.status.isin(["passed", "failed", "unavailable"]).all():
        raise ValueError("Measurement audit contains an unknown result status")
    expected = {(pitch, metric) for pitch in EXAMPLE_IDS for metric in SIGNALS}
    observed = set(rows[["session_pitch", "metric"]].itertuples(index=False, name=None))
    complete = observed == expected
    passed = int(rows.status.eq("passed").sum())
    return {
        "scope": SCOPE,
        "n_checks": len(rows),
        "n_expected_checks": len(expected),
        "n_passed": passed,
        "n_failed": int(rows.status.eq("failed").sum()),
        "n_unavailable": int(rows.status.eq("unavailable").sum()),
        "n_pitches": int(rows.session_pitch.nunique()),
        "n_metrics": int(rows.metric.nunique()),
        "complete": complete,
        "all_passed": complete and passed == len(expected),
        "tolerance": TOLERANCE,
        "interpretation": INTERPRETATION,
    }
