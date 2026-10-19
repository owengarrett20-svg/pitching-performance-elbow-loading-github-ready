"""Athlete-held-out descriptive baselines for pitching POI measurements.

These are associations among measurements from the same pitch. Neither the
features nor the predictions constitute a pre-pitch forecast or injury model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = (
    "age_yrs",
    "session_mass_kg",
    "session_height_m",
    "max_shoulder_internal_rotational_velo",
    "max_rotation_hip_shoulder_separation",
    "max_torso_rotational_velo",
)
TARGETS = ("pitch_speed_mph", "elbow_varus_moment")
RIDGE_ALPHA = 10.0


@dataclass(frozen=True)
class ModelResults:
    """Out-of-fold results and the information required to audit their splits."""

    predictions: pd.DataFrame
    metrics: pd.DataFrame
    fold_metrics: pd.DataFrame
    fold_assignments: pd.DataFrame
    split_audit: list[dict[str, Any]]
    feature_manifest: dict[str, Any]


def _metric_row(frame: pd.DataFrame) -> dict[str, Any]:
    observed = frame["observed"].to_numpy(dtype=float)
    residual = frame["residual"].to_numpy(dtype=float)
    squared_total = float(np.sum((observed - observed.mean()) ** 2))
    # A constant outcome has no variance to explain; do not replace undefined R²
    # with a seemingly meaningful 0 or 1.
    r2 = (
        float(1.0 - np.sum(residual**2) / squared_total)
        if len(frame) >= 2 and squared_total > 0
        else float("nan")
    )
    return {
        "n_pitches": len(frame),
        "n_athletes": int(frame["user"].nunique()),
        "mae": float(frame["absolute_error"].mean()),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "r2": r2,
        "athlete_mae": float(frame.groupby("user")["absolute_error"].mean().mean()),
    }


def _numeric_column(data: pd.DataFrame, name: str) -> pd.Series:
    try:
        return pd.to_numeric(data[name], errors="raise").astype(float)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Column {name!r} must contain numeric values or missing values") from exc


def evaluate_baselines(data: pd.DataFrame, n_splits: int = 5, seed: int = 42) -> ModelResults:
    """Evaluate mean and fixed-alpha ridge models on unseen athletes.

    One shuffled GroupKFold partition is made before any target filtering and
    reused for both outcomes. Missing/nonfinite outcomes are omitted separately
    for each target; they are never imputed. All predictor preprocessing is fit
    only to the training rows with an observed target in the current fold.

    The ridge penalty is fixed a priori, with no parameter search on these
    evaluation folds. Metrics describe this cohort and do not establish causal
    effects, injury risk, or generalization to another population.
    """
    required = {"session_pitch", "user", *FEATURES, *TARGETS}
    missing_columns = sorted(required - set(data.columns))
    if missing_columns:
        raise ValueError(f"Missing required model columns: {', '.join(missing_columns)}")
    if not isinstance(n_splits, int) or isinstance(n_splits, bool) or n_splits < 2:
        raise ValueError("n_splits must be an integer of at least 2")
    if data.empty:
        raise ValueError("Cannot evaluate an empty pitching table")

    # Copy and reset so duplicate external DataFrame indexes cannot misalign
    # observed outcomes, group labels, or the held-out predictions.
    table = data.reset_index(drop=True).copy()
    for identifier in ("session_pitch", "user"):
        if table[identifier].isna().any():
            raise ValueError(f"{identifier} must not contain missing identifiers")
        table[identifier] = table[identifier].astype(str)
        if table[identifier].str.strip().eq("").any():
            raise ValueError(f"{identifier} must not contain empty identifiers")
    if table["session_pitch"].duplicated().any():
        raise ValueError("session_pitch must identify one pitch per row")

    n_groups = int(table["user"].nunique())
    if n_groups < n_splits:
        raise ValueError(f"Need at least {n_splits} athletes; found {n_groups}")

    features = pd.DataFrame({name: _numeric_column(table, name) for name in FEATURES})
    nonfinite_feature_counts = {
        name: int(np.isinf(features[name].to_numpy()).sum()) for name in FEATURES
    }
    features = features.replace([np.inf, -np.inf], np.nan)
    targets = {name: _numeric_column(table, name) for name in TARGETS}
    finite_targets = {name: np.isfinite(values.to_numpy()) for name, values in targets.items()}
    for name, valid in finite_targets.items():
        if not valid.any():
            raise ValueError(f"No finite observed target values for {name}")
        if table.loc[valid, "user"].nunique() < 2:
            raise ValueError(f"Need observed {name} values from at least two athletes")

    splitter = GroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    folds = list(splitter.split(features, groups=table["user"]))
    fold_numbers = np.full(len(table), -1, dtype=int)
    audit: list[dict[str, Any]] = []
    prediction_parts: list[pd.DataFrame] = []

    for fold, (train_indices, test_indices) in enumerate(folds, start=1):
        fold_numbers[test_indices] = fold
        train_athletes = sorted(table.iloc[train_indices]["user"].unique().tolist())
        test_athletes = sorted(table.iloc[test_indices]["user"].unique().tolist())
        overlap = sorted(set(train_athletes) & set(test_athletes))
        if overlap:
            raise RuntimeError("Athlete leakage detected in cross-validation partition")
        fold_audit: dict[str, Any] = {
            "fold": fold,
            "train_athletes": train_athletes,
            "test_athletes": test_athletes,
            "n_train_athletes": len(train_athletes),
            "n_test_athletes": len(test_athletes),
            "n_train_pitches": len(train_indices),
            "n_test_pitches": len(test_indices),
            "athlete_overlap": len(overlap),
            "targets": {},
        }
        for target in TARGETS:
            valid = finite_targets[target]
            target_train = train_indices[valid[train_indices]]
            target_test = test_indices[valid[test_indices]]
            fold_audit["targets"][target] = {
                "n_train_observed": len(target_train),
                "n_test_observed": len(target_test),
                "all_missing_train_features": [
                    name for name in FEATURES if features.iloc[target_train][name].isna().all()
                ],
            }
            if not len(target_train):
                raise ValueError(f"Fold {fold} has no observed training targets for {target}")
            if not len(target_test):
                continue
            x_train = features.iloc[target_train]
            x_test = features.iloc[target_test]
            y_train = targets[target].iloc[target_train]
            y_test = targets[target].iloc[target_test].to_numpy()
            models = {
                "dummy_mean": DummyRegressor(strategy="mean"),
                "ridge": Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(
                                strategy="median", add_indicator=True, keep_empty_features=True
                            ),
                        ),
                        ("scaler", StandardScaler()),
                        ("regressor", Ridge(alpha=RIDGE_ALPHA)),
                    ]
                ),
            }
            for model_name, model in models.items():
                model.fit(x_train, y_train)
                predicted = np.asarray(model.predict(x_test), dtype=float)
                residual = y_test - predicted
                prediction_parts.append(
                    pd.DataFrame(
                        {
                            "session_pitch": table.iloc[target_test]["session_pitch"].to_numpy(),
                            "user": table.iloc[target_test]["user"].to_numpy(),
                            "fold": fold,
                            "target": target,
                            "model": model_name,
                            "observed": y_test,
                            "predicted": predicted,
                            "residual": residual,
                            "absolute_error": np.abs(residual),
                        }
                    )
                )
        audit.append(fold_audit)

    predictions = pd.concat(prediction_parts, ignore_index=True)
    metrics = pd.DataFrame(
        [
            {"target": target, "model": model, **_metric_row(frame)}
            for (target, model), frame in predictions.groupby(["target", "model"], sort=True)
        ]
    )
    fold_metrics = pd.DataFrame(
        [
            {"target": target, "model": model, "fold": int(fold), **_metric_row(frame)}
            for (target, model, fold), frame in predictions.groupby(
                ["target", "model", "fold"], sort=True
            )
        ]
    )
    assignments = table[["session_pitch", "user"]].copy()
    assignments["fold"] = fold_numbers
    manifest: dict[str, Any] = {
        "features": list(FEATURES),
        "targets": list(TARGETS),
        "models": {
            "dummy_mean": {"strategy": "training_fold_mean"},
            "ridge": {"alpha": RIDGE_ALPHA, "tuning": "none; fixed a priori"},
        },
        "splitter": "GroupKFold",
        "group": "user",
        "n_splits": n_splits,
        "shuffle": True,
        "seed": seed,
        "shared_target_folds": True,
        "feature_preprocessing": {
            "nonfinite": "replace positive/negative infinity with missing",
            "imputation": "training-fold median with missingness indicators",
            "all_missing_training_feature": "keep feature; impute zero as technical fallback",
            "scaling": "training-fold StandardScaler after imputation",
            "fit_scope": "training rows with finite target only, within each fold",
        },
        "nonfinite_feature_counts": nonfinite_feature_counts,
        "target_policy": "exclude missing/nonfinite targets separately; never impute outcomes",
        "excluded_target_rows": {
            name: int((~valid).sum()) for name, valid in finite_targets.items()
        },
        "metrics": {
            "residual": "observed minus predicted",
            "mae": "pooled held-out pitch mean absolute error",
            "rmse": "pooled held-out pitch root mean squared error",
            "r2": "pooled held-out R²; undefined for fewer than two or constant observations",
            "athlete_mae": "unweighted mean of per-athlete held-out MAE",
        },
        "excluded_predictors": [
            "athlete/session/pitch identifiers",
            "filenames and paths",
            "both outcome columns, including duplicated metadata pitch speed",
            "unlisted source measurements",
        ],
        "interpretation": (
            "Same-pitch post-motion descriptive associations, not pre-pitch forecasts. "
            "Joint moment is not an injury probability or a validated injury predictor. "
            "No causal inference or synchronized video availability is assumed."
        ),
    }
    return ModelResults(predictions, metrics, fold_metrics, assignments, audit, manifest)


def save_model_results(results: ModelResults, output_dir: str | Path) -> None:
    """Write auditable out-of-fold artifacts without serializing fitted models."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for filename, frame in (
        ("oof_predictions.csv", results.predictions),
        ("model_metrics.csv", results.metrics),
        ("fold_metrics.csv", results.fold_metrics),
        ("fold_assignments.csv", results.fold_assignments),
    ):
        frame.to_csv(output / filename, index=False)
    for filename, value in (
        ("split_audit.json", results.split_audit),
        ("model_spec.json", results.feature_manifest),
    ):
        (output / filename).write_text(
            json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
