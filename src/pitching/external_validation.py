"""Freeze numerical baselines, then evaluate a separately authorized new cohort.

No external observations are read by ``freeze_models``. Evaluation reconstructs
only numerical prediction operations from JSON; it never unpickles an object,
fits a model, selects predictors, or changes the frozen protocol. These local
tools establish an auditable workflow, not evidence that an external study has
already been completed or that an owner's attestations have been independently
verified.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from pitching.models import FEATURES, RIDGE_ALPHA, TARGETS, _metric_row
from pitching.new_data import DEFINITIONS, UNITS
from pitching.phase2 import FEATURE_SETS

_GENERATOR = "pitching.external_validation"
_BUNDLE_FILES = {
    "models.json",
    "protocol.json",
    "development_provenance.json",
    "freeze_metadata.json",
}
_CANONICAL_UNITS = {name: UNITS[name] for name in (*FEATURES, *TARGETS)}
_RIGHTS_NOTICE = (
    "Model parameters derive from the development data and retain applicable input-data "
    "rights and restrictions. In particular, OBP-trained bundles retain OBP's data terms, "
    "including its professional-sports/financial-analysis affiliation exclusion. The "
    "original software's MIT license does not grant data or derived-model reuse rights. "
    "Authorization statements are supplied by the owner, not independently verified here."
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: dict | list) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _read_json(path: Path) -> dict:
    def invalid(value: str) -> None:
        raise ValueError(f"Nonfinite JSON number is not allowed: {value}")

    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular JSON file: {path.name}")

    def unique(pairs: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key in {path.name}: {key}")
            result[key] = item
        return result

    value = json.loads(path.read_bytes(), parse_constant=invalid, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")  # noqa: TRY004 - serialized value
    return value


def _new_output(path: Path, *protected: Path) -> Path:
    if path.is_symlink():
        raise ValueError("Output directory must not be a symlink")
    output = path.resolve()
    for source in protected:
        source = source.resolve()
        if output == source or output.is_relative_to(source):
            raise ValueError("Output directory must be separate from prepared inputs and bundles")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Refusing to overwrite a nonempty output directory")
    return output


def _versions() -> dict[str, str]:
    return {
        name: importlib.metadata.version(name)
        for name in ("numpy", "pandas", "scikit-learn", "pitching-performance-elbow-loading")
    }


def _code_hashes() -> dict[str, str]:
    directory = Path(__file__).resolve().parent
    names = ("external_validation.py", "new_data.py", "models.py", "phase2.py")
    return {name: _sha((directory / name).read_bytes()) for name in names}


def _protocol(value: dict) -> dict:
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("External protocol must use schema_version 1")
    required_text = (
        "study_id",
        "research_question",
        "intended_external_population",
        "development_identity_namespace",
        "external_identity_namespace",
    )
    attestations = (
        "external_athletes_disjoint_attested",
        "external_outcomes_unseen_at_freeze_attested",
        "measurement_compatibility_reviewed",
    )
    allowed = {
        "schema_version",
        "evaluation_design",
        "prediction_context",
        *required_text,
        *attestations,
    }
    if set(value) != allowed:
        raise ValueError("The fixed external protocol contains missing or unsupported fields")
    for name in required_text:
        if (
            not isinstance(value.get(name), str)
            or not value[name].strip()
            or value[name] != value[name].strip()
            or value[name].startswith("EDIT_")
        ):
            raise ValueError(f"Complete the protocol field {name!r} before freezing")
    if value.get("evaluation_design") != "independent_new_athletes":
        raise ValueError("This workflow supports independent_new_athletes only")
    if value.get("prediction_context") != "same_pitch_post_motion":
        raise ValueError("The fixed rotational summaries support same_pitch_post_motion only")
    for name in attestations:
        if value.get(name) is not True:
            raise ValueError(f"The responsible investigator must explicitly attest {name!r}")
    forbidden = {"features", "targets", "models", "alpha", "hyperparameters"}.intersection(value)
    if forbidden:
        raise ValueError("This kit fixes the predictors, outcomes, four models, and alpha at 10")
    return value


def _numeric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"session_pitch", "user", "session", *FEATURES, *TARGETS}
    if not required.issubset(frame):
        raise ValueError("Prepared dataset is missing canonical identifiers or measurements")
    if frame.empty:
        raise ValueError("Cannot use an empty prepared dataset")
    numbers = frame[list(FEATURES) + list(TARGETS)].apply(pd.to_numeric, errors="raise")
    if np.isinf(numbers.to_numpy(dtype=float)).any():
        raise ValueError("Prepared measurements must be finite numbers or genuinely missing")
    return numbers


def _namespace(provenance: dict) -> str:
    dataset = provenance.get("dataset", {})
    if not isinstance(dataset, dict):
        raise ValueError("Prepared dataset declarations must be an object")  # noqa: TRY004 - serialized value
    namespace = dataset.get("athlete_id_namespace")
    if not isinstance(namespace, str) or not namespace.strip() or namespace != namespace.strip():
        raise ValueError("Prepared data must declare its athlete_id_namespace")
    rights = dataset.get("rights", {})
    if (
        not isinstance(rights, dict)
        or rights.get("authorized") is not True
        or not isinstance(rights.get("basis"), str)
    ):
        raise ValueError("Prepared data must retain an explicit authorization basis")
    if not rights["basis"].strip():
        raise ValueError("Prepared data authorization basis must be nonempty")
    return namespace


def _measurement_contract(prepared: Path) -> dict:
    mapping = _read_json(prepared / "mapping.json")
    columns = mapping.get("columns", {})
    contract = {}
    for name in (*FEATURES, *TARGETS):
        declaration = columns.get(name, {})
        definition = declaration.get("definition")
        if not isinstance(definition, str) or not definition.strip():
            raise ValueError(f"Missing reviewed measurement definition for {name}")
        if declaration.get("definition_confirmed") is not True:
            raise ValueError(f"Measurement definition has not been confirmed for {name}")
        contract[name] = {
            "canonical_unit": _CANONICAL_UNITS[name],
            "definition": definition.strip(),
        }
    return contract


def _measurement_fingerprint(numbers: pd.DataFrame) -> str:
    """Detect wholesale development reuse even if IDs or row order were changed."""
    columns = list(FEATURES) + list(TARGETS)
    ordered = numbers[columns].sort_values(columns, na_position="last", kind="stable")
    return _sha(ordered.to_csv(index=False, float_format="%.17g", lineterminator="\n").encode())


def _profiles(frame: pd.DataFrame) -> dict:
    profiles = {}
    for name in FEATURES:
        values = frame[name].dropna().astype(float)
        profiles[name] = {
            "n_rows": len(frame),
            "n_missing": int(frame[name].isna().sum()),
            "minimum": float(values.min()) if len(values) else None,
            "maximum": float(values.max()) if len(values) else None,
            "mean": float(values.mean()) if len(values) else None,
            "median": float(values.median()) if len(values) else None,
        }
    return profiles


def _ridge_parameters(x: pd.DataFrame, y: pd.Series) -> dict:
    model = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
            ),
            ("scaler", StandardScaler()),
            ("regressor", Ridge(alpha=RIDGE_ALPHA)),
        ]
    ).fit(x, y)
    imputer = model.named_steps["imputer"]
    scaler = model.named_steps["scaler"]
    regressor = model.named_steps["regressor"]
    return {
        "features": list(x.columns),
        "alpha": RIDGE_ALPHA,
        "imputation_statistics": imputer.statistics_.tolist(),
        "missing_indicator_features": imputer.indicator_.features_.tolist(),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coefficients": regressor.coef_.tolist(),
        "intercept": float(regressor.intercept_),
    }


def _validate_models(models: dict) -> None:
    if set(models) != set(TARGETS):
        raise ValueError("Frozen bundle must contain both fixed outcomes")
    for target in TARGETS:
        if not isinstance(models[target], dict) or set(models[target]) != set(FEATURE_SETS):
            raise ValueError("Frozen bundle must contain all four fixed models")
        for name, allowed in FEATURE_SETS.items():
            parameters = models[target][name]
            if not isinstance(parameters, dict):
                raise ValueError("Model parameters must be JSON objects")  # noqa: TRY004 - serialized value
            if name == "dummy_mean":
                if set(parameters) != {"constant"} or not _finite_number(parameters["constant"]):
                    raise ValueError("Frozen mean must be finite")
                continue
            expected = {
                "features",
                "alpha",
                "imputation_statistics",
                "missing_indicator_features",
                "scaler_mean",
                "scaler_scale",
                "coefficients",
                "intercept",
            }
            if set(parameters) != expected or parameters["features"] != list(allowed):
                raise ValueError("Frozen feature names/order differ from the fixed specification")
            if not _finite_number(parameters["alpha"]) or parameters["alpha"] != RIDGE_ALPHA:
                raise ValueError("Frozen ridge penalty differs from the fixed specification")
            indicators = parameters["missing_indicator_features"]
            if (
                not isinstance(indicators, list)
                or any(
                    type(value) is not int or value < 0 or value >= len(allowed)
                    for value in indicators
                )
                or indicators != sorted(set(indicators))
            ):
                raise ValueError("Invalid training missing-indicator ordering")
            lengths = {
                "imputation_statistics": len(allowed),
                "scaler_mean": len(allowed) + len(indicators),
                "scaler_scale": len(allowed) + len(indicators),
                "coefficients": len(allowed) + len(indicators),
            }
            for field, length in lengths.items():
                values = parameters[field]
                if (
                    not isinstance(values, list)
                    or len(values) != length
                    or any(not _finite_number(value) for value in values)
                ):
                    raise ValueError(f"Invalid frozen numerical vector: {field}")
            if np.any(np.asarray(parameters["scaler_scale"]) <= 0):
                raise ValueError("Frozen scales must be strictly positive")
            if not _finite_number(parameters["intercept"]):
                raise ValueError("Frozen intercept must be finite")


def _finite_number(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _digest_string(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_metadata(metadata: dict, provenance: dict, protocol: dict) -> None:
    """Reject internally inconsistent, even freshly rehashed, bundle components.

    This is structural integrity checking. A party that replaces all files and
    hashes can create a different coherent bundle; hashes do not authenticate an
    investigator, their data, permissions, or independence attestations.
    """
    if (
        type(metadata.get("schema_version")) is not int
        or metadata["schema_version"] != 1
        or metadata.get("type") != "frozen_development_models"
        or metadata.get("study_id") != protocol["study_id"]
        or metadata.get("development_namespace") != protocol["development_identity_namespace"]
        or _namespace(provenance) != protocol["development_identity_namespace"]
        or metadata.get("development_data_rights") != provenance["dataset"]["rights"]
    ):
        raise ValueError("Frozen metadata, provenance, and protocol are inconsistent")
    for field, prepared_field in (
        ("development_source_sha256", "source_csv_sha256"),
        ("development_canonical_sha256", "canonical_csv_sha256"),
    ):
        if not _digest_string(metadata.get(field)) or metadata[field] != provenance.get(
            prepared_field
        ):
            raise ValueError("Frozen development input hashes differ from their provenance")
    if not _digest_string(metadata.get("development_measurement_sha256")):
        raise ValueError("Frozen measurement fingerprint must be a SHA-256 digest")
    prepared_hashes = provenance.get("artifacts_sha256")
    if (
        not isinstance(prepared_hashes, dict)
        or set(prepared_hashes)
        != {"canonical.csv", "mapping.json", "audit.json", "missingness.csv"}
        or any(not _digest_string(value) for value in prepared_hashes.values())
        or prepared_hashes["canonical.csv"] != provenance["canonical_csv_sha256"]
        or prepared_hashes["mapping.json"] != provenance.get("mapping_sha256")
        or provenance.get("canonical_units") != UNITS
        or provenance.get("definitions") != DEFINITIONS
    ):
        raise ValueError("Frozen prepared provenance has an inconsistent canonical contract")
    for field in ("development_pitch_ids", "development_athlete_ids"):
        identifiers = metadata.get(field)
        if (
            not isinstance(identifiers, list)
            or not identifiers
            or any(
                not isinstance(value, str) or not value or value != value.strip()
                for value in identifiers
            )
            or identifiers != sorted(set(identifiers))
        ):
            raise ValueError("Frozen development identifiers must be unique sorted strings")
    pitches = len(metadata["development_pitch_ids"])
    athletes = len(metadata["development_athlete_ids"])
    if not 2 <= athletes <= pitches:
        raise ValueError("Frozen development membership counts are inconsistent")
    expected_contract = {
        name: {"canonical_unit": UNITS[name], "definition": DEFINITIONS[name]}
        for name in (*FEATURES, *TARGETS)
    }
    if metadata.get("measurement_contract") != expected_contract:
        raise ValueError("Frozen measurement contract differs from the canonical definitions")
    code = metadata.get("code_sha256")
    packages = metadata.get("packages")
    if (
        not isinstance(code, dict)
        or set(code) != {"external_validation.py", "new_data.py", "models.py", "phase2.py"}
        or any(not _digest_string(value) for value in code.values())
        or not isinstance(packages, dict)
        or set(packages)
        != {"numpy", "pandas", "scikit-learn", "pitching-performance-elbow-loading"}
        or any(not isinstance(value, str) or not value for value in packages.values())
        or metadata.get("rights_notice") != _RIGHTS_NOTICE
    ):
        raise ValueError("Frozen producing-code, package, or rights metadata are incomplete")
    summaries = metadata.get("training_summary")
    if not isinstance(summaries, dict) or set(summaries) != set(TARGETS):
        raise ValueError("Frozen training summaries must identify both outcomes")
    for summary in summaries.values():
        if not isinstance(summary, dict):
            raise ValueError("Frozen training summary must be an object")  # noqa: TRY004 - serialized value
        for field in ("n_observed_pitches", "n_observed_athletes", "n_excluded_missing_outcomes"):
            if type(summary.get(field)) is not int or summary[field] < 0:
                raise ValueError("Frozen training counts must be nonnegative integers")
        observed = summary["n_observed_pitches"]
        if observed + summary["n_excluded_missing_outcomes"] != pitches or not 2 <= summary[
            "n_observed_athletes"
        ] <= min(athletes, observed):
            raise ValueError("Frozen training counts differ from development membership")
        profiles = summary.get("predictor_profiles")
        if not isinstance(profiles, dict) or set(profiles) != set(FEATURES):
            raise ValueError("Frozen training profiles must contain the six fixed predictors")
        for profile in profiles.values():
            if (
                not isinstance(profile, dict)
                or type(profile.get("n_rows")) is not int
                or profile["n_rows"] != observed
                or type(profile.get("n_missing")) is not int
                or not 0 <= profile["n_missing"] <= observed
            ):
                raise ValueError("Frozen predictor-profile counts are inconsistent")
            values = [profile.get(field) for field in ("minimum", "maximum", "mean", "median")]
            if profile["n_missing"] == observed:
                if values != [None] * 4:
                    raise ValueError("All-missing training profiles must retain missing summaries")
            elif any(not _finite_number(value) for value in values) or (
                values[0] > values[1]
                or any(value < values[0] - 1e-9 or value > values[1] + 1e-9 for value in values[2:])
            ):
                raise ValueError("Frozen training profile has invalid finite summary values")


def predict_frozen(models: dict, numbers: pd.DataFrame) -> dict[tuple[str, str], np.ndarray]:
    """Apply already frozen numerical parameters without fitting or reading targets."""
    _validate_models(models)
    predictions = {}
    for target in TARGETS:
        for name, parameters in models[target].items():
            if name == "dummy_mean":
                predicted = np.full(len(numbers), parameters["constant"], dtype=float)
            else:
                x = numbers[parameters["features"]].to_numpy(dtype=float)
                missing = np.isnan(x)
                x = np.where(missing, np.asarray(parameters["imputation_statistics"]), x)
                indicators = parameters["missing_indicator_features"]
                if indicators:
                    x = np.column_stack([x, missing[:, indicators].astype(float)])
                x = (x - parameters["scaler_mean"]) / parameters["scaler_scale"]
                predicted = x @ np.asarray(parameters["coefficients"]) + parameters["intercept"]
            if not np.isfinite(predicted).all():
                raise ValueError("Frozen prediction was nonfinite; review input ranges")
            predictions[(target, name)] = predicted
    return predictions


def freeze_models(prepared_dir: Path, protocol_path: Path, output_dir: Path) -> dict:
    """Fit on development data only and freeze a complete, hash-bound JSON bundle."""
    from pitching.new_data import load_prepared_dataset

    prepared = Path(prepared_dir).resolve()
    protocol_path = Path(protocol_path).resolve()
    output = _new_output(Path(output_dir), prepared)
    protocol = _protocol(_read_json(protocol_path))
    frame, provenance = load_prepared_dataset(prepared)
    namespace = _namespace(provenance)
    if namespace != protocol["development_identity_namespace"]:
        raise ValueError("Development namespace differs from the frozen protocol declaration")
    numbers = _numeric_frame(frame)
    if frame.user.nunique() < 2:
        raise ValueError("Development data must contain at least two athletes")
    models, training_summary = {}, {}
    for target in TARGETS:
        valid = numbers[target].notna()
        if not valid.any() or frame.loc[valid, "user"].nunique() < 2:
            raise ValueError(
                f"Need observed {target} values from at least two development athletes"
            )
        x = numbers.loc[valid, list(FEATURES)]
        y = numbers.loc[valid, target]
        models[target] = {"dummy_mean": {"constant": float(y.mean())}}
        for name, allowed in FEATURE_SETS.items():
            if name != "dummy_mean":
                models[target][name] = _ridge_parameters(x[list(allowed)], y)
        training_summary[target] = {
            "n_observed_pitches": int(valid.sum()),
            "n_observed_athletes": int(frame.loc[valid, "user"].nunique()),
            "n_excluded_missing_outcomes": int((~valid).sum()),
            "predictor_profiles": _profiles(x),
        }
    _validate_models(models)
    metadata = {
        "schema_version": 1,
        "type": "frozen_development_models",
        "created_utc": datetime.now(UTC).isoformat(),
        "study_id": protocol["study_id"],
        "packages": _versions(),
        "code_sha256": _code_hashes(),
        "development_namespace": namespace,
        "development_pitch_ids": sorted(frame.session_pitch.astype(str).tolist()),
        "development_athlete_ids": sorted(frame.user.astype(str).unique().tolist()),
        "development_source_sha256": provenance["source_csv_sha256"],
        "development_canonical_sha256": provenance["canonical_csv_sha256"],
        "development_measurement_sha256": _measurement_fingerprint(numbers),
        "measurement_contract": _measurement_contract(prepared),
        "training_summary": training_summary,
        "development_data_rights": provenance["dataset"]["rights"],
        "rights_notice": _RIGHTS_NOTICE,
        "interpretation": (
            "All eligible development rows were used to fit these deployment parameters. "
            "This fit is not cross-validation, and no in-sample score is external evidence. "
            "These models describe same-pitch post-motion associations, not future-pitch "
            "forecasts, tissue forces, causal interventions, or injury probability."
        ),
    }
    _validate_metadata(metadata, provenance, protocol)
    payloads = {
        "models.json": _json_bytes(models),
        "protocol.json": _json_bytes(protocol),
        "development_provenance.json": _json_bytes(provenance),
        "freeze_metadata.json": _json_bytes(metadata),
    }
    manifest = {
        "schema_version": 1,
        "generator": _GENERATOR,
        "files": {name: _sha(payload) for name, payload in payloads.items()},
        "integrity_scope": "Checksums detect accidental edits; they are not an authenticity signature.",
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        (output / name).write_bytes(payload)
    (output / "manifest.json").write_bytes(_json_bytes(manifest))
    return manifest


def load_frozen_bundle(bundle_dir: Path) -> tuple[dict, dict, dict, dict]:
    """Verify exact file names and hashes before accepting numerical model parameters."""
    directory = Path(bundle_dir)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Frozen bundle must be a regular directory")
    manifest = _read_json(directory / "manifest.json")
    if (
        type(manifest.get("schema_version")) is not int
        or manifest["schema_version"] != 1
        or manifest.get("generator") != _GENERATOR
    ):
        raise ValueError("Unknown frozen bundle format")
    files = manifest.get("files")
    if (
        not isinstance(files, dict)
        or set(files) != _BUNDLE_FILES
        or any(not _digest_string(digest) for digest in files.values())
    ):
        raise ValueError("Frozen bundle must list exactly its four required JSON files")
    for name, digest in files.items():
        path = directory / name
        if path.is_symlink() or not path.is_file() or _sha(path.read_bytes()) != digest:
            raise ValueError(f"Frozen bundle checksum mismatch: {name}")
    models = _read_json(directory / "models.json")
    protocol = _protocol(_read_json(directory / "protocol.json"))
    metadata = _read_json(directory / "freeze_metadata.json")
    provenance = _read_json(directory / "development_provenance.json")
    _validate_models(models)
    _validate_metadata(metadata, provenance, protocol)
    return models, protocol, metadata, provenance


def _shift_table(numbers: pd.DataFrame, metadata: dict) -> pd.DataFrame:
    rows = []
    for target in TARGETS:
        training = metadata["training_summary"][target]["predictor_profiles"]
        for name, profile in _profiles(numbers).items():
            observed = numbers[name].dropna()
            low, high = training[name]["minimum"], training[name]["maximum"]
            outside = int(((observed < low) | (observed > high)).sum()) if low is not None else None
            rows.append(
                {
                    "target_model_training_subset": target,
                    "feature": name,
                    "unit": _CANONICAL_UNITS[name],
                    "development_observed_minimum": low,
                    "development_observed_maximum": high,
                    "external_minimum": profile["minimum"],
                    "external_maximum": profile["maximum"],
                    "external_mean": profile["mean"],
                    "external_n_rows": len(numbers),
                    "external_n_missing": profile["n_missing"],
                    "external_n_outside_development_range": outside,
                }
            )
    return pd.DataFrame(rows)


def evaluate_external(prepared_dir: Path, bundle_dir: Path, output_dir: Path) -> dict:
    """Evaluate already frozen models on a separately prepared, attested new cohort."""
    from pitching.new_data import load_prepared_dataset

    prepared, bundle = Path(prepared_dir).resolve(), Path(bundle_dir).resolve()
    output = _new_output(Path(output_dir), prepared, bundle)
    models, protocol, metadata, development_provenance = load_frozen_bundle(bundle)
    frame, provenance = load_prepared_dataset(prepared)
    namespace = _namespace(provenance)
    if namespace != protocol["external_identity_namespace"]:
        raise ValueError("External namespace differs from the frozen protocol declaration")
    if _measurement_contract(prepared) != metadata["measurement_contract"]:
        raise ValueError("External measurement definitions differ from the frozen contract")
    numbers = _numeric_frame(frame)
    if (
        provenance["source_csv_sha256"] == metadata["development_source_sha256"]
        or provenance["canonical_csv_sha256"] == metadata["development_canonical_sha256"]
        or _measurement_fingerprint(numbers) == metadata["development_measurement_sha256"]
    ):
        raise ValueError("External data reuse the development input or complete measurement table")
    same_namespace = namespace == metadata["development_namespace"]
    athlete_overlap = set(frame.user.astype(str)) & set(metadata["development_athlete_ids"])
    pitch_overlap = set(frame.session_pitch.astype(str)) & set(metadata["development_pitch_ids"])
    if same_namespace and (athlete_overlap or pitch_overlap):
        raise ValueError(
            "Development and external athletes/pitches overlap in the shared namespace"
        )
    warnings = []
    if not same_namespace:
        warnings.append(
            "Athlete namespaces differ. Automated ID checks cannot establish that people are "
            "different across namespaces. Independence relies on the investigator's explicit "
            "disjoint-athlete attestation and their separate identity review."
        )
    warnings.append(
        "The freeze-time statements about unseen outcomes, permissions, and measurement "
        "compatibility are investigator attestations, not independently verified facts."
    )
    predictions = predict_frozen(models, numbers)
    parts, metrics = [], []
    for (target, name), predicted in predictions.items():
        observed = numbers[target].to_numpy(dtype=float)
        with np.errstate(over="ignore", invalid="ignore"):
            residual = observed - predicted
        if not np.isfinite(residual[np.isfinite(observed)]).all():
            raise ValueError(
                "External errors overflowed; review the measurement units and numerical ranges"
            )
        rows = frame[["session_pitch", "user", "session"]].copy()
        rows["target"], rows["model"] = target, name
        rows["observed"], rows["predicted"] = observed, predicted
        rows["residual"], rows["absolute_error"] = residual, np.abs(residual)
        rows["outcome_observed"] = np.isfinite(observed)
        parts.append(rows)
        measured = rows.loc[rows.outcome_observed]
        metric = {
            "target": target,
            "model": name,
            "n_prediction_rows": len(rows),
            "n_missing_outcomes": int((~rows.outcome_observed).sum()),
            "status": "evaluated" if len(measured) else "no_observed_outcomes",
        }
        with np.errstate(over="ignore", invalid="ignore"):
            evaluated = (
                _metric_row(measured)
                if len(measured)
                else {
                    "n_pitches": 0,
                    "n_athletes": 0,
                    "mae": np.nan,
                    "rmse": np.nan,
                    "r2": np.nan,
                    "athlete_mae": np.nan,
                }
            )
        if len(measured) and any(
            not np.isfinite(evaluated[field]) for field in ("mae", "rmse", "athlete_mae")
        ):
            raise ValueError(
                "External metrics overflowed; review the measurement units and numerical ranges"
            )
        metric.update(evaluated)
        metrics.append(metric)
    prediction_table = pd.concat(parts, ignore_index=True)
    metric_table = pd.DataFrame(metrics)
    athlete_errors = pd.DataFrame(
        [
            {
                "target": target,
                "model": model,
                "user": athlete,
                "n_observed_pitches": len(group),
                "mae": float(group.absolute_error.mean()),
            }
            for (target, model, athlete), group in prediction_table.loc[
                prediction_table.outcome_observed
            ].groupby(["target", "model", "user"], sort=True)
        ],
        columns=["target", "model", "user", "n_observed_pitches", "mae"],
    )
    shift = _shift_table(numbers, metadata)
    audit = {
        "schema_version": 1,
        "type": "frozen_external_evaluation",
        "completed_utc": datetime.now(UTC).isoformat(),
        "study_id": protocol["study_id"],
        "frozen_manifest_sha256": _sha((bundle / "manifest.json").read_bytes()),
        "evaluation_code_sha256": _code_hashes(),
        "packages": _versions(),
        "n_external_pitches": len(frame),
        "n_external_athletes": int(frame.user.nunique()),
        "n_external_sessions": int(frame.session.nunique()),
        "identity_check": {
            "same_namespace": same_namespace,
            "known_shared_namespace_athlete_overlap": len(athlete_overlap)
            if same_namespace
            else None,
            "known_shared_namespace_pitch_overlap": len(pitch_overlap) if same_namespace else None,
            "cross_namespace_raw_id_collisions_are_not_identity_proof": not same_namespace,
            "disjoint_athletes_attested": True,
        },
        "development_dataset": development_provenance["dataset"],
        "external_dataset": provenance["dataset"],
        "external_source_csv_sha256": provenance["source_csv_sha256"],
        "external_canonical_csv_sha256": provenance["canonical_csv_sha256"],
        "external_prepared_provenance_sha256": _sha((prepared / "provenance.json").read_bytes()),
        "training_performed": False,
        "target_imputation_performed": False,
        "warnings": warnings,
        "rights_notice": _RIGHTS_NOTICE,
        "interpretation": (
            "Descriptive external errors for frozen same-pitch post-motion models, with equal-athlete "
            "MAE as the primary summary. No confidence intervals, causal effects, injury probabilities, "
            "future-session generalization, or guaranteed improvements are asserted. An external "
            "cohort's independence and measurement compatibility require substantive human review."
        ),
    }
    lines = [
        "# Frozen external evaluation",
        "",
        "This report was generated from the actual local external input named in evaluation_audit.json.",
        "No model was fitted or selected on this evaluation cohort. Outcomes were never imputed.",
        "",
        "The primary error is the unweighted mean of each evaluated athlete's mean absolute error.",
        "Pooled pitch MAE and RMSE are separate summaries. Missing outcomes are excluded per target.",
        "Undefined R² remains missing (including constant outcomes or fewer than two observations).",
        "",
        metric_table.to_csv(index=False),
        "Per-athlete errors and observed-pitch counts are retained in external_athlete_errors.csv.",
        "## Scope and review",
        "",
        "See covariate_shift.csv for observed feature ranges and missingness. Its comparisons",
        "use each outcome model's actual eligible development rows and all external prediction rows.",
        "Different instruments, conventions, populations, or collection protocols can change transportability.",
        "The preparation metadata retain both datasets' population and collection-protocol declarations.",
        "",
        *warnings,
        "",
        audit["interpretation"],
        "",
        _RIGHTS_NOTICE,
        "",
        "These files include athlete-level measurements. Keep them in the agreed private environment;",
        "do not copy them into the public reference snapshot or a public GitHub issue.",
    ]
    payloads = {
        "external_predictions.csv": prediction_table.to_csv(index=False).encode(),
        "external_metrics.csv": metric_table.to_csv(index=False).encode(),
        "external_athlete_errors.csv": athlete_errors.to_csv(index=False).encode(),
        "covariate_shift.csv": shift.to_csv(index=False).encode(),
        "evaluation_audit.json": _json_bytes(audit),
        "external_provenance.json": _json_bytes(provenance),
        "external_report.md": ("\n".join(lines) + "\n").encode(),
    }
    manifest = {
        "schema_version": 1,
        "generator": _GENERATOR,
        "type": "completed_external_evaluation",
        "files": {name: _sha(payload) for name, payload in payloads.items()},
        "frozen_manifest_sha256": audit["frozen_manifest_sha256"],
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        (output / name).write_bytes(payload)
    (output / "evaluation_manifest.json").write_bytes(_json_bytes(manifest))
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser(
        "freeze", help="Fit authorized development data and freeze JSON parameters"
    )
    freeze.add_argument("--prepared", type=Path, required=True)
    freeze.add_argument("--protocol", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    evaluate = commands.add_parser(
        "evaluate", help="Apply frozen models to a separately prepared new cohort"
    )
    evaluate.add_argument("--prepared", type=Path, required=True)
    evaluate.add_argument("--bundle", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            result = freeze_models(args.prepared, args.protocol, args.output)
            print(f"Frozen development bundle: {len(result['files'])} verified JSON artifacts.")
            print("No external dataset was read or evaluated. " + _RIGHTS_NOTICE)
        else:
            result = evaluate_external(args.prepared, args.bundle, args.output)
            print(f"Completed local frozen evaluation: {len(result['files'])} artifacts.")
            print(
                "No fitting was performed. Review identity, measurement, permission, and cohort-shift audit notes."
            )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"External workflow stopped: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
