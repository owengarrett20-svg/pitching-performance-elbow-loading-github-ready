"""Extract canonical processed traces without inventing a camera synchronization.

These are exported OBP signals. We do not rerun inverse dynamics or claim that
their processing windows can be recovered from the POI names alone.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from pitching.data import COMMIT, METADATA_PATH, POI_PATH

EXAMPLE_IDS = ("1393_3", "1623_3", "2916_4")
EVENTS = ("pkh_time", "fp_10_time", "fp_100_time", "MER_time", "BR_time", "MIR_time")
ARCHIVES = {
    "pitching_joint_angles.zip": {
        "sha256": "b4c4854ffcc52a0f757e0b3a3c86acdc4a2fc2e50516a76e62aabdb916afed46",
        "csv": "joint_angles.csv",
        "columns": ["torso_pelvis_angle_z"],
    },
    "pitching_joint_velos.zip": {
        "sha256": "5752f571b40acc4f02afc42dcfdb4b9eb191fcffd5fb25bc3c585e149941fb69",
        "csv": "joint_velos.csv",
        "columns": ["shoulder_velo_z", "torso_velo_z"],
    },
    "pitching_forces_moments.zip": {
        "sha256": "ff96d23cfccd3a43473c591166fab1c4317019cd0aec999611e8dc8401246a02",
        "csv": "forces_moments.csv",
        "columns": ["elbow_moment_y"],
    },
}
SIGNALS = {
    "max_rotation_hip_shoulder_separation": {
        "column": "hip_shoulder_separation_deg",
        "raw_column": "torso_pelvis_angle_z",
        "sign": 1,
        "label": "Hip–shoulder separation",
        "unit": "deg",
    },
    "max_shoulder_internal_rotational_velo": {
        "column": "shoulder_internal_rotation_velocity_deg_s",
        "raw_column": "shoulder_velo_z",
        "sign": 1,
        "label": "Canonical shoulder z rotation velocity",
        "unit": "deg/s",
    },
    "max_torso_rotational_velo": {
        "column": "torso_rotation_velocity_deg_s",
        "raw_column": "torso_velo_z",
        "sign": 1,
        "label": "Torso axial rotation velocity",
        "unit": "deg/s",
    },
    "elbow_varus_moment": {
        "column": "elbow_varus_moment_nm",
        "raw_column": "elbow_moment_y",
        "sign": 1,
        "label": "Internal elbow varus moment",
        "unit": "N·m",
    },
}


def _selected_archive(path: Path, spec: dict, ids: tuple[str, ...]) -> pd.DataFrame:
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != spec["sha256"]:
        raise ValueError(f"Canonical release checksum mismatch: {path.name}")
    columns = ["session_pitch", "time", *EVENTS, *spec["columns"]]
    parts = []
    with zipfile.ZipFile(path) as archive, archive.open(spec["csv"]) as csv:
        for chunk in pd.read_csv(
            csv, usecols=columns, dtype={"session_pitch": "string"}, chunksize=100_000
        ):
            selected = chunk.loc[chunk.session_pitch.isin(ids)]
            if len(selected):
                parts.append(selected)
    if not parts:
        raise ValueError(f"None of the selected pitch IDs exists in {path.name}")
    result = pd.concat(parts, ignore_index=True).sort_values(["session_pitch", "time"])
    if result.duplicated(["session_pitch", "time"]).any():
        raise ValueError(f"Duplicate pitch/time keys in {path.name}")
    if set(result.session_pitch) != set(ids):
        raise ValueError(f"Missing requested pitch in {path.name}")
    return result.reset_index(drop=True)


def join_traces(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    """Reject missing frame coverage or conflicting events instead of inner-joining."""
    keys = ["session_pitch", "time"]
    merged = left.merge(
        right,
        on=keys,
        how="outer",
        validate="one_to_one",
        suffixes=("", "_other"),
        indicator=True,
        sort=True,
    )
    if not merged._merge.eq("both").all():
        raise ValueError("Processed trace time grids differ; do not silently discard samples.")
    for event in EVENTS:
        if not np.allclose(
            merged[event], merged[event + "_other"], equal_nan=True, rtol=0, atol=1e-9
        ):
            raise ValueError(f"Conflicting {event} between canonical trace tables.")
    return merged.drop(columns=["_merge", *(event + "_other" for event in EVENTS)])


def add_convention_aliases(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep released signs; do not infer velocity negation from an angle label.

    In all three checked examples, the stored positive shoulder_velo_z maximum
    equals the published peak internal-rotation POI. The broad README kinematic
    sign table alone does not establish how all export adjustments were applied.
    """
    result = frame.copy()
    for signal in SIGNALS.values():
        result[signal["column"]] = signal["sign"] * result[signal["raw_column"]]
    return result


def prepare_trace_examples(project_root: Path, ids: tuple[str, ...] = EXAMPLE_IDS) -> dict:
    root = Path(project_root)
    output = root / "assets/traces"
    output.mkdir(parents=True, exist_ok=True)
    merged = None
    archives = []
    for filename, spec in ARCHIVES.items():
        path = root / "data/visual-source" / filename
        frame = _selected_archive(path, spec, ids)
        merged = frame if merged is None else join_traces(merged, frame)
        archives.append(
            {
                "file": filename,
                "sha256": spec["sha256"],
                "csv": spec["csv"],
                "bytes": path.stat().st_size,
                "url": f"https://github.com/drivelineresearch/openbiomechanics/releases/download/dataset-v1/{filename}",
            }
        )
    merged = add_convention_aliases(merged)
    poi = pd.read_csv(root / "data/raw" / POI_PATH, dtype={"session_pitch": "string"})
    metadata = pd.read_csv(
        root / "data/raw" / METADATA_PATH, dtype={"session_pitch": "string", "user": "string"}
    )
    examples = []
    for pitch_id in ids:
        selected = merged.loc[merged.session_pitch.eq(pitch_id)].reset_index(drop=True)
        if not selected.time.is_monotonic_increasing or selected.time.duplicated().any():
            raise ValueError(f"Nonmonotonic processed time: {pitch_id}")
        trial = poi.loc[poi.session_pitch.eq(pitch_id)].squeeze()
        meta = metadata.loc[metadata.session_pitch.eq(pitch_id)].squeeze()
        path = output / f"{pitch_id}.csv"
        selected.to_csv(path, index=False)
        comparisons = []
        for metric, signal in SIGNALS.items():
            values = selected[signal["column"]]
            finite = values.notna() & np.isfinite(values)
            maximum = float(values[finite].max()) if finite.any() else None
            event_values = {}
            for event in EVENTS:
                unique = selected[event].dropna().unique()
                if len(unique) > 1:
                    raise ValueError(f"Event varies within pitch {pitch_id}: {event}")
                event_values[event] = float(unique[0]) if len(unique) else None
            comparisons.append(
                {
                    "metric": metric,
                    "source_column": signal["raw_column"],
                    "display_column": signal["column"],
                    "sign": signal["sign"],
                    "unit": signal["unit"],
                    "published_poi": float(trial[metric]),
                    "trace_max": maximum,
                    "n_missing": int((~finite).sum()),
                    "selection": "Maximum finite value over the entire released trace; not a claimed POI window reconstruction.",
                }
            )
        examples.append(
            {
                "session_pitch": pitch_id,
                "user": str(meta.user),
                "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "n_samples": len(selected),
                "events": event_values,
                "comparison": comparisons,
            }
        )
    manifest = {
        "schema_version": 1,
        "source_commit": COMMIT,
        "release_tag": "dataset-v1",
        "archives": archives,
        "signals": SIGNALS,
        "examples": examples,
        "time_basis": "Original processed CSV time in seconds; no verified raw-C3D or camera synchronization is asserted.",
        "scope": "Released processed signals only. This project does not independently recompute Visual3D joint dynamics.",
        "shoulder_convention_note": "shoulder_velo_z is retained as released, without negation. Its positive maximum matches the published internal-rotation POI in all three prepared examples. The generic README external(+)/internal(-) kinematic label does not document the complete export sign-adjustment pipeline; do not infer an Euler-angle derivative or silently flip this trace.",
        "license_url": f"https://github.com/drivelineresearch/openbiomechanics/blob/{COMMIT}/LICENSE-DATA.md",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return manifest
