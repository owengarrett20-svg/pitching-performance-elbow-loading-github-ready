"""Immutable-source download and documented-schema pitching data validation.

OBP's official loader uses pandas.read_csv on these same paths. This module uses
the documented schema directly, adding strict cardinality and overlap checks.
It does not infer observations, repair targets, or silently multiply trials.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd

REPOSITORY = "https://github.com/drivelineresearch/openbiomechanics"
COMMIT = "44b98dae05cceb016f080ab39d105c85b8639084"
POI_PATH = "baseball_pitching/data/poi/poi_metrics.csv"
METADATA_PATH = "baseball_pitching/data/metadata.csv"
DICTIONARY_PATH = "baseball_pitching/data/data_dictionary.csv"
VARIABLES = {
    "pitch_speed_mph": ("Pitch speed", "mph"),
    "elbow_varus_moment": ("Peak internal elbow varus moment", "N·m"),
    "max_shoulder_internal_rotational_velo": ("Peak shoulder internal rotation velocity", "deg/s"),
    "max_rotation_hip_shoulder_separation": ("Peak hip–shoulder separation", "deg"),
    "max_torso_rotational_velo": ("Peak torso axial rotation velocity", "deg/s"),
}
METADATA_FIELDS = (
    "user",
    "session_mass_kg",
    "session_height_m",
    "age_yrs",
    "playing_level",
    "filename_new",
    "modelname_new",
)


class DataValidationError(ValueError):
    """A schema or relationship failure; report retains the audit evidence."""

    def __init__(self, message: str, report: dict | None = None):
        super().__init__(message)
        self.report = report or {}


def read_manifest(path: Path) -> dict:
    manifest = json.loads(Path(path).read_text())
    if manifest["repository"] != REPOSITORY or manifest["commit"] != COMMIT:
        raise DataValidationError("Manifest must identify the reviewed, pinned OBP revision.")
    return manifest


def fetch_source(manifest_path: Path, data_dir: Path) -> dict:
    """Download only manifest-listed files, with HTTPS and pinned SHA-256 checks.

    Existing files must match; corrupted/locally edited files are not overwritten.
    Cache paths retain the official directory structure. No GitHub token is needed.
    """
    manifest = read_manifest(manifest_path)
    data_dir = Path(data_dir).resolve()
    verified = []
    for entry in manifest["files"]:
        relative = Path(entry["path"])
        destination = (data_dir / relative).resolve()
        if relative.is_absolute() or not destination.is_relative_to(data_dir):
            raise DataValidationError("Manifest file path escapes the data directory.")
        if destination.exists():
            contents = destination.read_bytes()
        else:
            url = f"https://raw.githubusercontent.com/drivelineresearch/openbiomechanics/{COMMIT}/{relative.as_posix()}"
            with urlopen(url, timeout=60) as response:
                contents = response.read()
        digest = hashlib.sha256(contents).hexdigest()
        if digest != entry["sha256"] or len(contents) != entry["bytes"]:
            raise DataValidationError(
                f"Checksum/size mismatch: {relative}. Preserve any local edits, then remove "
                "that cached file and fetch again. Expected checksums must not be changed to bypass this."
            )
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".part")
            temporary.write_bytes(contents)
            os.replace(temporary, destination)
        verified.append({"path": relative.as_posix(), "sha256": digest, "bytes": len(contents)})
    return {"repository": REPOSITORY, "commit": COMMIT, "files": verified}


def verify_source(manifest_path: Path, data_dir: Path) -> dict:
    """Offline integrity check. Analysis never silently fetches changed data."""
    manifest = read_manifest(manifest_path)
    for entry in manifest["files"]:
        path = Path(data_dir) / entry["path"]
        if not path.is_file():
            raise DataValidationError(
                f"Source cache incomplete: {path}. Run `pitching fetch` first."
            )
        contents = path.read_bytes()
        if (
            hashlib.sha256(contents).hexdigest() != entry["sha256"]
            or len(contents) != entry["bytes"]
        ):
            raise DataValidationError(f"Source cache checksum/size mismatch: {path}")
    return {"repository": REPOSITORY, "commit": COMMIT, "verified_files": len(manifest["files"])}


def read_source(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Use the official documented CSV schema, retaining IDs as strings."""
    poi = pd.read_csv(
        Path(data_dir) / POI_PATH, dtype={"session_pitch": "string", "session": "string"}
    )
    metadata = pd.read_csv(
        Path(data_dir) / METADATA_PATH,
        dtype={"session_pitch": "string", "session": "string", "user": "string"},
    )
    return poi, metadata


def missingness_table(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    """Report absent values and nonfinite numeric cells separately, without filling."""
    rows = []
    for column in frame.columns:
        values = frame[column]
        missing = values.isna()
        if pd.api.types.is_string_dtype(values) or values.dtype == object:
            missing = missing | values.astype("string").str.strip().eq("").fillna(False)
        n_nonfinite = 0
        if pd.api.types.is_numeric_dtype(values):
            n_nonfinite = int(np.isinf(values.to_numpy(dtype=float, na_value=np.nan)).sum())
        rows.append(
            {
                "table": name,
                "column": column,
                "n_rows": len(frame),
                "n_missing": int(missing.sum()),
                "pct_missing": float(100 * missing.mean()) if len(frame) else 0.0,
                "n_infinite": n_nonfinite,
            }
        )
    return pd.DataFrame(rows)


def _key_audit(frame: pd.DataFrame, key: str) -> dict:
    if key not in frame:
        return {"missing_column": True}
    values = frame[key].astype("string")
    invalid = values.isna() | values.str.strip().eq("").fillna(False)
    invalid |= values.ne(values.str.strip()).fillna(False)
    duplicate = values.duplicated(keep=False) & ~invalid
    return {
        "n_rows": len(frame),
        "invalid_key_rows": int(invalid.sum()),
        "duplicate_key_rows": int(duplicate.sum()),
        "duplicate_keys": sorted(values[duplicate].dropna().unique().tolist()),
    }


def join_pitching(poi: pd.DataFrame, metadata: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Require one-to-one pitch coverage and consistent duplicate source fields."""
    audit = {"status": "checking", "join_key": "session_pitch", "cardinality": "one_to_one"}
    audit["poi"] = _key_audit(poi, "session_pitch")
    audit["metadata"] = _key_audit(metadata, "session_pitch")

    def fail(message: str) -> None:
        audit["status"] = "failed"
        audit["error"] = message
        raise DataValidationError(message, audit)

    required_poi = {"session_pitch", "session", "p_throws", "pitch_type", *VARIABLES}
    required_meta = {"session_pitch", "session", "pitch_speed_mph", *METADATA_FIELDS}
    missing_poi = sorted(required_poi - set(poi.columns))
    missing_meta = sorted(required_meta - set(metadata.columns))
    if missing_poi or missing_meta:
        fail(f"Required schema columns missing: POI={missing_poi}, metadata={missing_meta}")
    for name in ("poi", "metadata"):
        if audit[name]["invalid_key_rows"] or audit[name]["duplicate_key_rows"]:
            fail(f"{name} pitch IDs must be nonempty, trimmed, and unique.")
    for name, frame, columns in (
        ("poi", poi, ("session",)),
        ("metadata", metadata, ("user", "session")),
    ):
        for column in columns:
            values = frame[column].astype("string")
            if (values.isna() | values.str.strip().eq("").fillna(False)).any():
                fail(
                    f"{name}.{column} cannot be missing: athlete grouping/session integrity requires it."
                )
    numeric = set(VARIABLES) | {"age_yrs", "session_height_m", "session_mass_kg"}
    for name, frame in (("poi", poi), ("metadata", metadata)):
        for column in sorted(numeric.intersection(frame.columns)):
            # Never coerce an invalid token into an invented missing value.
            if not pd.api.types.is_numeric_dtype(frame[column]):
                fail(
                    f"{name}.{column} must contain numeric measurements or genuine missing values."
                )
            if np.isinf(frame[column].to_numpy(dtype=float, na_value=np.nan)).any():
                fail(
                    f"{name}.{column} contains infinite measurements; investigate source integrity."
                )
    left = set(poi.session_pitch.astype(str))
    right = set(metadata.session_pitch.astype(str))
    audit["poi_only_keys"] = sorted(left - right)
    audit["metadata_only_keys"] = sorted(right - left)
    if left != right:
        fail("POI/metadata pitch coverage differs; unmatched pitches must be investigated.")
    merged = poi.merge(
        metadata,
        on="session_pitch",
        how="outer",
        validate="one_to_one",
        suffixes=("", "_metadata"),
        indicator=True,
        sort=True,
    )
    if not merged["session"].astype(str).equals(merged["session_metadata"].astype(str)):
        fail("POI and metadata session identifiers disagree.")
    both = merged.pitch_speed_mph.notna() & merged.pitch_speed_mph_metadata.notna()
    conflicts = both & ~np.isclose(
        merged.pitch_speed_mph, merged.pitch_speed_mph_metadata, rtol=0, atol=1e-9, equal_nan=True
    )
    audit["duplicate_speed_conflicts"] = int(conflicts.sum())
    audit["duplicate_speed_missing_pairs"] = int((~both).sum())
    if conflicts.any():
        fail("Pitch speed differs between POI and metadata; do not choose or average silently.")
    if metadata.groupby("session")["user"].nunique().gt(1).any():
        fail("A session maps to multiple athletes.")
    analysis = merged.drop(columns=["session_metadata", "pitch_speed_mph_metadata", "_merge"])
    audit.update(
        {
            "status": "passed",
            "n_joined_pitches": len(analysis),
            "n_athletes": int(analysis.user.nunique()),
            "n_sessions": int(analysis.session.nunique()),
            "pitch_types": {
                str(k): int(v) for k, v in analysis.pitch_type.value_counts(dropna=False).items()
            },
            "pitch_hand": {
                str(k): int(v) for k, v in analysis.p_throws.value_counts(dropna=False).items()
            },
            "pitches_per_athlete": analysis.groupby("user").size().describe().to_dict(),
            "target_policy": "POI outcomes retained; metadata does not fill missing targets.",
        }
    )
    return analysis.reset_index(drop=True), audit


def audit_dataset(data_dir: Path) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    poi, metadata = read_source(data_dir)
    analysis, audit = join_pitching(poi, metadata)
    missing = pd.concat(
        [
            missingness_table(poi, "poi"),
            missingness_table(metadata, "metadata"),
            missingness_table(analysis, "analysis"),
        ],
        ignore_index=True,
    )
    dictionary = pd.read_csv(Path(data_dir) / DICTIONARY_PATH)
    expected = set(dictionary.loc[dictionary.dataset.eq("pitching_poi"), "column"])
    if set(poi.columns) != expected:
        raise DataValidationError(
            "POI columns disagree with the pinned official data dictionary.", audit
        )
    audit["schema_reference"] = DICTIONARY_PATH
    audit["source_commit"] = COMMIT
    audit["columns_with_missing_poi"] = int(
        missing.query("table == 'poi' and n_missing > 0").shape[0]
    )
    audit["requested_variables_missing"] = (
        missing.loc[
            missing.table.eq("analysis") & missing.column.isin(VARIABLES), ["column", "n_missing"]
        ]
        .set_index("column")
        .n_missing.to_dict()
    )
    return analysis, audit, missing
