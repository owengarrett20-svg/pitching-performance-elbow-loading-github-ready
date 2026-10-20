"""Local, explicit-schema preparation of independently authorized pitching tables.

This adapter checks declarations and data integrity. It cannot establish legal
permission or biomechanical equivalence from a checkbox or a matching unit.
No table is uploaded and no model is fitted here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pitching.models import FEATURES, TARGETS

IDENTIFIERS = ("session_pitch", "user", "session")
CANONICAL_COLUMNS = (*IDENTIFIERS, *FEATURES, *TARGETS)
UNITS = {
    **dict.fromkeys(IDENTIFIERS, "identifier"),
    "age_yrs": "years",
    "session_mass_kg": "kg",
    "session_height_m": "m",
    "max_shoulder_internal_rotational_velo": "deg/s",
    "max_rotation_hip_shoulder_separation": "deg",
    "max_torso_rotational_velo": "deg/s",
    "pitch_speed_mph": "mph",
    "elbow_varus_moment": "N*m",
}
DEFINITIONS = {
    "session_pitch": "unique_pitch_identifier",
    "user": "stable_pseudonymous_athlete_identifier",
    "session": "unique_assessment_session_identifier",
    "age_yrs": "age_at_assessment",
    "session_mass_kg": "body_mass_at_assessment",
    "session_height_m": "body_height_at_assessment",
    "max_shoulder_internal_rotational_velo": "peak_internal_shoulder_rotation_angular_velocity",
    "max_rotation_hip_shoulder_separation": "peak_thorax_pelvis_separation_angle",
    "max_torso_rotational_velo": "peak_torso_axial_rotation_angular_velocity",
    "pitch_speed_mph": "recorded_pitch_speed",
    "elbow_varus_moment": "peak_internal_net_elbow_varus_moment",
}
SIGNED_COLUMNS = {
    "max_shoulder_internal_rotational_velo",
    "max_rotation_hip_shoulder_separation",
    "max_torso_rotational_velo",
    "elbow_varus_moment",
}
MISSING_TOKENS = frozenset({"", "na", "n/a", "nan", "null", "none"})
_CONVERSIONS = {
    "identifier": {"identifier": 1.0},
    "years": {"years": 1.0},
    "kg": {"kg": 1.0, "lb": 0.45359237},
    "m": {"m": 1.0, "cm": 0.01},
    "deg/s": {"deg/s": 1.0, "rad/s": 180.0 / math.pi},
    "deg": {"deg": 1.0, "rad": 180.0 / math.pi},
    "mph": {"mph": 1.0, "m/s": 2.2369362920544025},
    "N*m": {"N*m": 1.0},
}
_ARTIFACT_NAMES = {"canonical.csv", "audit.json", "missingness.csv", "mapping.json"}
_DATASET_FIELDS = ("name", "population", "collection_protocol", "athlete_id_namespace")


class NewDataValidationError(ValueError):
    """The declared schema, permission attestation, or observed table is invalid."""


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value.strip().startswith("EDIT_"):
        raise NewDataValidationError(f"{label} requires a nonempty reviewed value")
    return value.strip()


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise NewDataValidationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _json(payload: bytes, label: str) -> dict:
    def invalid_constant(value: str) -> None:
        raise NewDataValidationError(f"Nonfinite JSON number in {label}: {value}")

    try:
        value = json.loads(
            payload.decode("utf-8-sig"),
            object_pairs_hook=_object_pairs,
            parse_constant=invalid_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise NewDataValidationError(f"Cannot read {label} as a UTF-8 JSON object") from error
    if not isinstance(value, dict):
        raise NewDataValidationError(f"{label} must contain a JSON object")
    return value


def validate_mapping(mapping: dict) -> dict:
    """Check explicit declarations; confirmation is a human attestation, not validation."""
    if type(mapping.get("schema_version")) is not int or mapping["schema_version"] != 1:
        raise NewDataValidationError("Mapping requires schema_version 1")
    dataset = mapping.get("dataset")
    if not isinstance(dataset, dict):
        raise NewDataValidationError("Mapping requires dataset metadata")
    for name in _DATASET_FIELDS:
        _text(dataset.get(name), f"dataset.{name}")
    namespace = dataset["athlete_id_namespace"]
    if namespace != namespace.strip():
        raise NewDataValidationError("dataset.athlete_id_namespace must not have edge whitespace")
    rights = dataset.get("rights")
    if not isinstance(rights, dict) or rights.get("authorized") is not True:
        raise NewDataValidationError("An authorized owner's rights attestation is required")
    _text(rights.get("basis"), "dataset.rights.basis")
    columns = mapping.get("columns")
    if not isinstance(columns, dict) or set(columns) != set(CANONICAL_COLUMNS):
        raise NewDataValidationError(
            "Mapping columns must contain exactly the three identifiers, six predictors, "
            "and two outcomes in the canonical schema"
        )
    sources = []
    for name in CANONICAL_COLUMNS:
        entry = columns[name]
        if not isinstance(entry, dict):
            raise NewDataValidationError(f"Mapping for {name} must be an object")
        source = _text(entry.get("source"), f"columns.{name}.source")
        if source != entry["source"]:
            raise NewDataValidationError(f"Source column name for {name} has edge whitespace")
        sources.append(source)
        if not isinstance(entry.get("unit"), str) or entry["unit"] not in _CONVERSIONS[UNITS[name]]:
            allowed = ", ".join(_CONVERSIONS[UNITS[name]])
            raise NewDataValidationError(f"Unsupported unit for {name}; choose {allowed}")
        if entry.get("definition") != DEFINITIONS[name]:
            raise NewDataValidationError(
                f"Definition for {name} does not match the required quantity"
            )
        if entry.get("definition_confirmed") is not True:
            raise NewDataValidationError(
                f"Review and confirm the measurement definition for {name}"
            )
        if name in SIGNED_COLUMNS:
            _text(entry.get("sign_convention"), f"columns.{name}.sign_convention")
            if entry.get("canonical_sign_confirmed") is not True:
                raise NewDataValidationError(f"Review and confirm the sign convention for {name}")
    if len(set(sources)) != len(sources):
        raise NewDataValidationError(
            "A source column cannot feed multiple canonical fields; duplicated mappings can leak outcomes"
        )
    return mapping


def _read_csv(payload: bytes, label: str) -> pd.DataFrame:
    try:
        contents = payload.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(contents), strict=True)
        header = next(reader)
        if (
            not header
            or any(not item.strip() for item in header)
            or len(set(header)) != len(header)
        ):
            raise NewDataValidationError(f"{label} has missing or duplicate CSV headers")
        for row in reader:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != len(header):
                raise NewDataValidationError(
                    f"{label} has a malformed row at CSV line {reader.line_num}: "
                    f"expected {len(header)} cells, found {len(row)}"
                )
        result = pd.read_csv(
            io.StringIO(contents), dtype="string", keep_default_na=False, na_filter=False
        )
    except (
        UnicodeDecodeError,
        StopIteration,
        csv.Error,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
    ) as error:
        raise NewDataValidationError(f"Cannot read {label} as a nonempty UTF-8 CSV") from error
    if result.empty:
        raise NewDataValidationError(f"{label} contains no pitch rows")
    return result


def _validate_identifiers(frame: pd.DataFrame) -> None:
    for name in IDENTIFIERS:
        values = frame[name].astype("string")
        if values.isna().any() or values.str.strip().eq("").any():
            raise NewDataValidationError(f"{name} contains missing or empty identifiers")
        if not values.eq(values.str.strip()).all():
            raise NewDataValidationError(f"{name} contains untrimmed identifiers")
    if frame.session_pitch.duplicated().any():
        raise NewDataValidationError("session_pitch must identify exactly one row per pitch")
    if frame.groupby("session")["user"].nunique().gt(1).any():
        raise NewDataValidationError("Each session must belong to exactly one athlete")


def _canonicalize(raw: pd.DataFrame, mapping: dict) -> tuple[pd.DataFrame, list[dict]]:
    columns = mapping["columns"]
    missing = {entry["source"] for entry in columns.values()} - set(raw)
    if missing:
        raise NewDataValidationError(f"CSV lacks mapped columns: {', '.join(sorted(missing))}")
    canonical = pd.DataFrame(index=raw.index)
    conversions = []
    for name in CANONICAL_COLUMNS:
        declaration = columns[name]
        values = raw[declaration["source"]].astype("string")
        if name in IDENTIFIERS:
            canonical[name] = values
            continue
        values = values.str.strip()
        absent = values.str.casefold().isin(MISSING_TOKENS)
        numeric = pd.to_numeric(values.mask(absent), errors="coerce").astype(float)
        invalid = ~absent & numeric.isna()
        if invalid.any():
            raise NewDataValidationError(
                f"{name} contains {int(invalid.sum())} invalid numeric cells"
            )
        if np.isinf(numeric.to_numpy()).any():
            raise NewDataValidationError(f"{name} contains nonfinite observed numeric values")
        multiplier = _CONVERSIONS[UNITS[name]][declaration["unit"]]
        with np.errstate(over="ignore", invalid="ignore"):
            converted = numeric * multiplier
        if np.isinf(converted.to_numpy()).any():
            raise NewDataValidationError(f"Unit conversion overflow for {name}")
        canonical[name] = converted
        conversions.append(
            {
                "column": name,
                "source_column": declaration["source"],
                "input_unit": declaration["unit"],
                "canonical_unit": UNITS[name],
                "multiplier": multiplier,
                "sign_changed": False,
            }
        )
    _validate_identifiers(canonical)
    for name in ("session_mass_kg", "session_height_m", "pitch_speed_mph"):
        if canonical[name].dropna().le(0).any():
            raise NewDataValidationError(f"Observed {name} values must be positive")
    if canonical.age_yrs.dropna().lt(0).any():
        raise NewDataValidationError("Observed age_yrs values cannot be negative")
    return canonical, conversions


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _missingness(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "column": name,
            "n_rows": len(frame),
            "n_missing": int(frame[name].isna().sum()),
            "fraction_missing": float(frame[name].isna().mean()),
            "unit": UNITS[name],
        }
        for name in CANONICAL_COLUMNS
    )


def _valid_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def prepare_dataset(csv_path: str | Path, mapping_path: str | Path, output_dir: str | Path) -> dict:
    """Validate a single already-joined table and write a new local prepared directory."""
    source, mapping_file, output = Path(csv_path), Path(mapping_path), Path(output_dir)
    if output.exists() or output.is_symlink():
        raise NewDataValidationError(
            "Output directory already exists; choose a new local directory"
        )
    source_bytes, mapping_bytes = source.read_bytes(), mapping_file.read_bytes()
    mapping = validate_mapping(_json(mapping_bytes, "mapping"))
    raw = _read_csv(source_bytes, "source CSV")
    canonical, conversions = _canonicalize(raw, mapping)
    canonical_bytes = canonical.to_csv(index=False).encode("utf-8")
    missingness = _missingness(canonical)
    audit = {
        "schema_version": 1,
        "status": "prepared",
        "source_csv_sha256": _digest(source_bytes),
        "mapping_sha256": _digest(mapping_bytes),
        "canonical_csv_sha256": _digest(canonical_bytes),
        "n_pitches": len(canonical),
        "n_athletes": int(canonical.user.nunique()),
        "n_sessions": int(canonical.session.nunique()),
        "one_row_per_pitch": True,
        "session_athlete_consistent": True,
        "input_join": "No join performed; input must already be a validated pitch-level table.",
        "missing_target_rows": {name: int(canonical[name].isna().sum()) for name in TARGETS},
        "all_missing_predictors": [name for name in FEATURES if canonical[name].isna().all()],
        "unmapped_source_column_count": len(raw.columns) - len(CANONICAL_COLUMNS),
        "identifier_policy": "Preserve identifier strings exactly; reject edge whitespace and empty IDs.",
        "numeric_missing_tokens": sorted(MISSING_TOKENS),
        "numeric_invalid_policy": "Reject nonnumeric, infinite, or overflowing observations.",
        "conversions": conversions,
        "semantic_review": "Human attestation only; no automatic sign or definition equivalence.",
    }
    payloads = {
        "canonical.csv": canonical_bytes,
        "audit.json": _json_bytes(audit),
        "missingness.csv": missingness.to_csv(index=False).encode("utf-8"),
        "mapping.json": mapping_bytes,
    }
    provenance = {
        "schema_version": 1,
        "type": "prepared_new_dataset",
        "created_utc": datetime.now(UTC).isoformat(),
        "dataset": mapping["dataset"],
        "source_csv_sha256": _digest(source_bytes),
        "mapping_sha256": _digest(mapping_bytes),
        "canonical_csv_sha256": _digest(payloads["canonical.csv"]),
        "canonical_units": UNITS,
        "definitions": DEFINITIONS,
        "artifacts_sha256": {name: _digest(payload) for name, payload in payloads.items()},
        "permission_status": "Data-owner attestation; not independently verified legal permission.",
        "measurement_status": "Declared definitions/signs require independent protocol review.",
        "analysis_status": "Prepared input only; no training, prediction, or external validation run.",
    }
    output.mkdir(parents=True, exist_ok=False)
    try:
        for name, payload in {**payloads, "provenance.json": _json_bytes(provenance)}.items():
            (output / name).write_bytes(payload)
    except OSError:
        shutil.rmtree(output)
        raise
    return provenance


def load_prepared_dataset(directory: str | Path) -> tuple[pd.DataFrame, dict]:
    """Read only the fixed prepared artifacts and verify hashes plus schema semantics."""
    root = Path(directory)
    if root.is_symlink():
        raise NewDataValidationError("Prepared dataset directories must not be symlinks")
    provenance_path = root / "provenance.json"
    if provenance_path.is_symlink():
        raise NewDataValidationError("Prepared artifacts must not be symlinks")
    provenance = _json(provenance_path.read_bytes(), "provenance")
    if (
        type(provenance.get("schema_version")) is not int
        or provenance["schema_version"] != 1
        or provenance.get("type") != "prepared_new_dataset"
    ):
        raise NewDataValidationError("Unknown prepared dataset format")
    hashes = provenance.get("artifacts_sha256")
    if not isinstance(hashes, dict) or set(hashes) != _ARTIFACT_NAMES:
        raise NewDataValidationError("Prepared artifact checksum manifest is incomplete")
    if not all(_valid_digest(value) for value in hashes.values()) or not all(
        _valid_digest(provenance.get(name))
        for name in ("source_csv_sha256", "mapping_sha256", "canonical_csv_sha256")
    ):
        raise NewDataValidationError("Prepared checksums must be lowercase SHA-256 digests")
    payloads = {}
    for name in sorted(_ARTIFACT_NAMES):
        artifact = root / name
        if artifact.is_symlink():
            raise NewDataValidationError("Prepared artifacts must not be symlinks")
        payload = artifact.read_bytes()
        if _digest(payload) != hashes[name]:
            raise NewDataValidationError(f"Prepared artifact checksum mismatch: {name}")
        payloads[name] = payload
    mapping = validate_mapping(_json(payloads["mapping.json"], "prepared mapping"))
    audit = _json(payloads["audit.json"], "prepared audit")
    if (
        type(audit.get("schema_version")) is not int
        or audit["schema_version"] != 1
        or audit.get("status") != "prepared"
        or audit.get("one_row_per_pitch") is not True
        or audit.get("session_athlete_consistent") is not True
    ):
        raise NewDataValidationError("Prepared audit is not a completed canonical table audit")
    if (
        _digest(payloads["mapping.json"]) != provenance.get("mapping_sha256")
        or _digest(payloads["canonical.csv"]) != provenance.get("canonical_csv_sha256")
        or mapping["dataset"] != provenance.get("dataset")
        or provenance.get("canonical_units") != UNITS
        or provenance.get("definitions") != DEFINITIONS
        or any(
            provenance.get(name) != audit.get(name)
            for name in ("source_csv_sha256", "mapping_sha256", "canonical_csv_sha256")
        )
    ):
        raise NewDataValidationError(
            "Prepared provenance differs from its mapping or canonical schema"
        )
    canonical = _read_csv(payloads["canonical.csv"], "canonical CSV")
    if list(canonical.columns) != list(CANONICAL_COLUMNS):
        raise NewDataValidationError("Prepared canonical columns differ from the fixed schema")
    identity_mapping = {
        **mapping,
        "columns": {
            name: {**mapping["columns"][name], "source": name, "unit": UNITS[name]}
            for name in CANONICAL_COLUMNS
        },
    }
    canonical, _ = _canonicalize(canonical, identity_mapping)
    if (
        not all(type(audit.get(name)) is int for name in ("n_pitches", "n_athletes", "n_sessions"))
        or audit.get("n_pitches") != len(canonical)
        or audit.get("n_athletes") != canonical.user.nunique()
        or audit.get("n_sessions") != canonical.session.nunique()
    ):
        raise NewDataValidationError("Prepared audit counts differ from the canonical table")
    if audit.get("missing_target_rows") != {
        name: int(canonical[name].isna().sum()) for name in TARGETS
    } or audit.get("all_missing_predictors") != [
        name for name in FEATURES if canonical[name].isna().all()
    ]:
        raise NewDataValidationError("Prepared audit missingness differs from the canonical table")
    if payloads["missingness.csv"] != _missingness(canonical).to_csv(index=False).encode("utf-8"):
        raise NewDataValidationError("Prepared missingness report differs from the canonical table")
    expected_conversions = [
        {
            "column": name,
            "source_column": mapping["columns"][name]["source"],
            "input_unit": mapping["columns"][name]["unit"],
            "canonical_unit": UNITS[name],
            "multiplier": _CONVERSIONS[UNITS[name]][mapping["columns"][name]["unit"]],
            "sign_changed": False,
        }
        for name in (*FEATURES, *TARGETS)
    ]
    if audit.get("conversions") != expected_conversions:
        raise NewDataValidationError("Prepared conversion audit differs from the reviewed mapping")
    return canonical, provenance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a local authorized pitching dataset")
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit", help="Validate a mapped CSV; never fit or upload")
    audit.add_argument("--csv", type=Path, required=True)
    audit.add_argument("--mapping", type=Path, required=True)
    audit.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        prepare_dataset(args.csv, args.mapping, args.output)
    except (OSError, ValueError) as error:
        print(f"New-data audit failed: {error}", file=sys.stderr)
        return 1
    print(
        "Prepared local dataset. Permission and measurement equivalence remain owner attestations."
    )
    print("No data were uploaded, no models were fitted, and no external results were established.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
