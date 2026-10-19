"""Prespecified predictor ablations and athlete-cluster error resampling.

The bootstrap conditions on fixed out-of-fold predictions. It does not refit
models or quantify the uncertainty of training an entire prediction pipeline.
Repeated grouped partitions are a sensitivity check, not independent samples.
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

from pitching.models import (
    FEATURES,
    RIDGE_ALPHA,
    TARGETS,
    ModelResults,
    _metric_row,
    _numeric_column,
)

ANTHROPOMETRIC_FEATURES = FEATURES[:3]
KINEMATIC_FEATURES = FEATURES[3:]
FEATURE_SETS = {
    "dummy_mean": (),
    "ridge_anthropometric": ANTHROPOMETRIC_FEATURES,
    "ridge_kinematic": KINEMATIC_FEATURES,
    "ridge_combined": FEATURES,
}
COMPARISONS = (
    ("ridge_combined", "ridge_anthropometric"),
    ("ridge_combined", "ridge_kinematic"),
    ("ridge_kinematic", "ridge_anthropometric"),
    ("ridge_anthropometric", "dummy_mean"),
    ("ridge_kinematic", "dummy_mean"),
    ("ridge_combined", "dummy_mean"),
)
DEFAULT_SENSITIVITY_SEEDS = tuple(range(42, 52))


@dataclass(frozen=True)
class Phase2Results:
    """Auditable predictions, paired comparisons, and partition sensitivity."""

    primary_predictions: pd.DataFrame
    primary_metrics: pd.DataFrame
    primary_fold_metrics: pd.DataFrame
    primary_fold_assignments: pd.DataFrame
    primary_split_audit: list[dict[str, Any]]
    athlete_errors: pd.DataFrame
    athlete_differences: pd.DataFrame
    comparisons: pd.DataFrame
    bootstrap_samples: pd.DataFrame
    sensitivity_predictions: pd.DataFrame
    sensitivity_metrics: pd.DataFrame
    sensitivity_fold_metrics: pd.DataFrame
    sensitivity_fold_assignments: pd.DataFrame
    sensitivity_athlete_errors: pd.DataFrame
    sensitivity_athlete_differences: pd.DataFrame
    sensitivity_comparisons: pd.DataFrame
    sensitivity_split_audit: list[dict[str, Any]]
    specification: dict[str, Any]


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if not isinstance(value, (int, np.integer)) or isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be an integer of at least {minimum}")
    if value < minimum or value > 2**32 - 1:
        raise ValueError(f"{name} must be between {minimum} and {2**32 - 1}")
    return int(value)


def _prepare(data: pd.DataFrame, n_splits: int):
    required = {"session_pitch", "user", *FEATURES, *TARGETS}
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Missing required model columns: {', '.join(missing)}")
    if data.empty:
        raise ValueError("Cannot evaluate an empty pitching table")
    table = data.reset_index(drop=True).copy()
    for name in ("session_pitch", "user"):
        if table[name].isna().any():
            raise ValueError(f"{name} must not contain missing identifiers")
        table[name] = table[name].astype(str)
        if table[name].str.strip().eq("").any():
            raise ValueError(f"{name} must not contain empty identifiers")
    if table.session_pitch.duplicated().any():
        raise ValueError("session_pitch must identify one pitch per row")
    if table.user.nunique() < n_splits:
        raise ValueError(f"Need at least {n_splits} athletes; found {table.user.nunique()}")
    features = pd.DataFrame({name: _numeric_column(table, name) for name in FEATURES})
    inf_counts = {name: int(np.isinf(features[name]).sum()) for name in FEATURES}
    features = features.replace([np.inf, -np.inf], np.nan)
    targets = {name: _numeric_column(table, name) for name in TARGETS}
    finite = {name: np.isfinite(values.to_numpy()) for name, values in targets.items()}
    for name, valid in finite.items():
        if not valid.any():
            raise ValueError(f"No finite observed target values for {name}")
        if table.loc[valid, "user"].nunique() < 2:
            raise ValueError(f"Need observed {name} values from at least two athletes")
    return table, features, targets, finite, inf_counts


def _evaluate_partition(data: pd.DataFrame, n_splits: int, seed: int) -> ModelResults:
    """Match Phase 1 folds and preprocessing exactly, with fixed feature sets."""
    table, features, targets, finite, inf_counts = _prepare(data, n_splits)
    splitter = GroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    assignments = table[["session_pitch", "user"]].copy()
    assignments["fold"] = -1
    audit: list[dict[str, Any]] = []
    parts: list[pd.DataFrame] = []
    for fold, (train, test) in enumerate(splitter.split(features, groups=table.user), start=1):
        assignments.loc[test, "fold"] = fold
        train_athletes = sorted(table.iloc[train].user.unique().tolist())
        test_athletes = sorted(table.iloc[test].user.unique().tolist())
        overlap = set(train_athletes) & set(test_athletes)
        if overlap:
            raise RuntimeError("Athlete leakage detected in cross-validation partition")
        split = {
            "fold": fold,
            "train_athletes": train_athletes,
            "test_athletes": test_athletes,
            "n_train_athletes": len(train_athletes),
            "n_test_athletes": len(test_athletes),
            "n_train_pitches": len(train),
            "n_test_pitches": len(test),
            "athlete_overlap": len(overlap),
            "targets": {},
        }
        for target in TARGETS:
            valid = finite[target]
            target_train = train[valid[train]]
            target_test = test[valid[test]]
            split["targets"][target] = {
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
            observed = targets[target].iloc[target_test].to_numpy()
            for model_name, allowed in FEATURE_SETS.items():
                if model_name == "dummy_mean":
                    model = DummyRegressor(strategy="mean")
                    # The dummy never uses its inputs; match Phase 1 input shape.
                    columns = list(FEATURES)
                else:
                    model = Pipeline(
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
                    )
                    columns = list(allowed)
                model.fit(features.iloc[target_train][columns], targets[target].iloc[target_train])
                predicted = np.asarray(
                    model.predict(features.iloc[target_test][columns]), dtype=float
                )
                if not np.isfinite(predicted).all():
                    raise ValueError(f"Nonfinite predictions from {model_name} for {target}")
                residual = observed - predicted
                parts.append(
                    pd.DataFrame(
                        {
                            "session_pitch": table.iloc[target_test].session_pitch.to_numpy(),
                            "user": table.iloc[target_test].user.to_numpy(),
                            "fold": fold,
                            "target": target,
                            "model": model_name,
                            "observed": observed,
                            "predicted": predicted,
                            "residual": residual,
                            "absolute_error": np.abs(residual),
                        }
                    )
                )
        audit.append(split)
    predictions = pd.concat(parts, ignore_index=True)
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
    spec = {
        "nonfinite_feature_counts": inf_counts,
        "excluded_target_rows": {target: int((~valid).sum()) for target, valid in finite.items()},
    }
    return ModelResults(predictions, metrics, fold_metrics, assignments, audit, spec)


def _paired_errors(predictions: pd.DataFrame, target: str) -> pd.DataFrame:
    """Align every model by pitch and require identical observations and groups."""
    selected = predictions.loc[predictions.target.eq(target)]
    reference = selected.loc[selected.model.eq("dummy_mean")].set_index("session_pitch")
    if reference.empty:
        raise ValueError(f"No prediction rows for {target}")
    if reference.user.nunique() < 2:
        raise ValueError(f"Need predictions from at least two athletes for {target}")
    keys = reference[["user", "fold", "observed"]].copy()
    base = keys.copy()
    for model in FEATURE_SETS:
        frame = selected.loc[selected.model.eq(model)].set_index("session_pitch")
        if set(frame.index) != set(base.index):
            raise ValueError(f"Unpaired pitch membership for {target}: {model}")
        frame = frame.reindex(base.index)
        if not frame[["user", "fold", "observed"]].equals(keys):
            raise ValueError(f"Unpaired athlete, fold, or observations for {target}: {model}")
        base[model] = frame.absolute_error
    # An athlete must have one held-out partition assignment within this target.
    if base.groupby("user").fold.nunique().gt(1).any():
        raise ValueError("An athlete appears in multiple folds")
    return base


def _validate_predictions(predictions: pd.DataFrame) -> None:
    required = {
        "session_pitch",
        "user",
        "fold",
        "target",
        "model",
        "observed",
        "predicted",
        "absolute_error",
    }
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Missing prediction columns: {', '.join(missing)}")
    if set(predictions.model) != set(FEATURE_SETS) or set(predictions.target) != set(TARGETS):
        raise ValueError(
            "Prediction models and targets must exactly match the Phase 2 specification"
        )
    if predictions[["session_pitch", "user", "fold", "target", "model"]].isna().any().any():
        raise ValueError("Prediction keys must not contain missing values")
    if predictions.duplicated(["session_pitch", "target", "model"]).any():
        raise ValueError("Duplicate prediction keys prevent paired comparison")
    try:
        folds = pd.to_numeric(predictions.fold, errors="raise").to_numpy(dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValueError("Prediction folds must be positive integers") from exc
    if not np.isfinite(folds).all() or (folds < 1).any() or (folds != np.floor(folds)).any():
        raise ValueError("Prediction folds must be positive integers")
    for name in ("session_pitch", "user"):
        if predictions[name].astype(str).str.strip().eq("").any():
            raise ValueError("Prediction identifiers must not be empty")
    values = predictions[["observed", "predicted", "absolute_error"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Prediction observations, predictions, and errors must be finite")
    if not np.allclose(values[:, 2], np.abs(values[:, 0] - values[:, 1]), rtol=1e-12, atol=1e-12):
        raise ValueError("absolute_error does not match observed and predicted values")
    if predictions.groupby("session_pitch").user.nunique().gt(1).any():
        raise ValueError("A pitch has inconsistent athlete assignments")
    if predictions.groupby("session_pitch").fold.nunique().gt(1).any():
        raise ValueError("A pitch has inconsistent fold assignments")
    if predictions.groupby("user").fold.nunique().gt(1).any():
        raise ValueError("An athlete appears in multiple folds")


def athlete_error_table(predictions: pd.DataFrame) -> pd.DataFrame:
    """Return one row per observed athlete, target, and model."""
    return (
        predictions.groupby(["target", "model", "user", "fold"], sort=True)
        .agg(
            n_pitches=("absolute_error", "size"),
            mae=("absolute_error", "mean"),
            rmse=("residual", lambda values: float(np.sqrt(np.mean(values**2)))),
            bias=("residual", "mean"),
        )
        .reset_index()
    )


def athlete_difference_table(predictions: pd.DataFrame) -> pd.DataFrame:
    """Return paired per-athlete MAE differences for every planned contrast."""
    parts = []
    for target in TARGETS:
        paired = _paired_errors(predictions, target)
        for model, reference in COMPARISONS:
            difference = paired.assign(difference=paired[model] - paired[reference])
            summary = (
                difference.groupby(["user", "fold"], sort=True)
                .agg(n_pitches=("difference", "size"), mae_difference=("difference", "mean"))
                .reset_index()
            )
            parts.append(summary.assign(target=target, model=model, reference=reference))
    return pd.concat(parts, ignore_index=True)[
        ["target", "model", "reference", "user", "fold", "n_pitches", "mae_difference"]
    ]


def _comparison_rows(predictions: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for target in TARGETS:
        paired = _paired_errors(predictions, target)
        for model, reference in COMPARISONS:
            differences = paired[model] - paired[reference]
            for metric, estimate in (
                ("athlete_mae", differences.groupby(paired.user).mean().mean()),
                ("mae", differences.mean()),
            ):
                rows.append(
                    {
                        "target": target,
                        "model": model,
                        "reference": reference,
                        "comparison": f"{model}_minus_{reference}",
                        "metric": metric,
                        "estimate": float(estimate),
                        "n_athletes": int(paired.user.nunique()),
                        "n_pitches": len(paired),
                        "primary": model == "ridge_combined"
                        and reference == "ridge_anthropometric"
                        and metric == "athlete_mae",
                    }
                )
    return rows


def compare_fixed_predictions(
    predictions: pd.DataFrame,
    *,
    bootstrap_replicates: int = 5000,
    bootstrap_seed: int = 20261019,
    confidence_level: float = 0.95,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Paired athlete-cluster percentile intervals for fixed OOF MAE differences.

    Sample n athletes with replacement from the n observed athletes for each
    outcome. All pitches belonging to a sampled athlete remain together, and
    duplicate selections retain their multiplicity. The same sampled athletes
    are used for every model pair within that outcome. No model is refitted.
    """
    replicates = _integer(bootstrap_replicates, "bootstrap_replicates", minimum=2)
    seed = _integer(bootstrap_seed, "bootstrap_seed")
    if not np.isfinite(confidence_level) or not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be finite and strictly between zero and one")
    _validate_predictions(predictions)
    rng = np.random.default_rng(seed)
    rows = _comparison_rows(predictions)
    samples = []
    for target in TARGETS:
        paired = _paired_errors(predictions, target)
        athletes = sorted(paired.user.unique())
        n_athletes = len(athletes)
        # Bound peak memory while preserving deterministic RNG draw order.
        chunks = []
        for start in range(0, replicates, 256):
            size = min(256, replicates - start)
            draws = rng.integers(0, n_athletes, size=(size, n_athletes))
            chunk: dict[tuple[str, str, str], np.ndarray] = {}
            for model, reference in COMPARISONS:
                differences = paired[model] - paired[reference]
                groups = differences.groupby(paired.user)
                counts = groups.size().reindex(athletes).to_numpy(dtype=float)
                sums = groups.sum().reindex(athletes).to_numpy(dtype=float)
                means = sums / counts
                chunk[(model, reference, "athlete_mae")] = means[draws].mean(axis=1)
                chunk[(model, reference, "mae")] = sums[draws].sum(axis=1) / counts[draws].sum(
                    axis=1
                )
            chunks.append(chunk)
        for row in [row for row in rows if row["target"] == target]:
            key = row["model"], row["reference"], row["metric"]
            values = np.concatenate([chunk[key] for chunk in chunks])
            tail = (1 - confidence_level) / 2
            low, high = np.quantile(values, [tail, 1 - tail], method="linear")
            row.update(
                ci_low=float(low),
                ci_high=float(high),
                confidence_level=float(confidence_level),
                bootstrap_replicates=replicates,
                bootstrap_seed=seed,
                interval_scope="fixed_oof_errors_athlete_cluster_percentile",
            )
            samples.append(
                pd.DataFrame(
                    {
                        "target": target,
                        "model": row["model"],
                        "reference": row["reference"],
                        "metric": row["metric"],
                        "replicate": np.arange(1, replicates + 1),
                        "difference": values,
                    }
                )
            )
    return pd.DataFrame(rows), pd.concat(samples, ignore_index=True)


def evaluate_phase2(
    data: pd.DataFrame,
    *,
    n_splits: int = 5,
    primary_seed: int = 42,
    sensitivity_seeds: tuple[int, ...] = DEFAULT_SENSITIVITY_SEEDS,
    bootstrap_replicates: int = 5000,
    bootstrap_seed: int = 20261019,
    confidence_level: float = 0.95,
) -> Phase2Results:
    """Fit the fixed feature ablations and prespecified sensitivity partitions."""
    n_splits = _integer(n_splits, "n_splits", minimum=2)
    primary_seed = _integer(primary_seed, "primary_seed")
    seeds = tuple(_integer(seed, "sensitivity_seed") for seed in sensitivity_seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("sensitivity_seeds must be a nonempty sequence of unique integer seeds")
    # Validate resampling arguments before model fitting starts.
    bootstrap_replicates = _integer(bootstrap_replicates, "bootstrap_replicates", minimum=2)
    bootstrap_seed = _integer(bootstrap_seed, "bootstrap_seed")
    if not np.isfinite(confidence_level) or not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be finite and strictly between zero and one")
    primary = _evaluate_partition(data, n_splits, primary_seed)
    comparisons, bootstrap_samples = compare_fixed_predictions(
        primary.predictions,
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
        confidence_level=confidence_level,
    )
    tables: dict[str, list[pd.DataFrame]] = {
        name: []
        for name in (
            "predictions",
            "metrics",
            "fold_metrics",
            "fold_assignments",
            "athletes",
            "athlete_differences",
            "comparisons",
        )
    }
    split_audit = []
    for seed in seeds:
        result = primary if seed == primary_seed else _evaluate_partition(data, n_splits, seed)
        frames = {
            "predictions": result.predictions,
            "metrics": result.metrics,
            "fold_metrics": result.fold_metrics,
            "fold_assignments": result.fold_assignments,
            "athletes": athlete_error_table(result.predictions),
            "athlete_differences": athlete_difference_table(result.predictions),
            "comparisons": pd.DataFrame(_comparison_rows(result.predictions)),
        }
        for name, frame in frames.items():
            tables[name].append(frame.assign(partition_seed=seed))
        split_audit.append({"partition_seed": seed, "folds": result.split_audit})
    combined = {name: pd.concat(frames, ignore_index=True) for name, frames in tables.items()}
    specification = {
        "schema_version": 1,
        "features": list(FEATURES),
        "targets": list(TARGETS),
        "models": {
            name: {
                "features": list(features),
                **(
                    {"strategy": "training_fold_mean"}
                    if name == "dummy_mean"
                    else {"alpha": RIDGE_ALPHA}
                ),
            }
            for name, features in FEATURE_SETS.items()
        },
        "primary_metric": "athlete_mae",
        "primary_comparison": "ridge_combined_minus_ridge_anthropometric",
        "comparison_direction": "model minus reference; negative favors model",
        "secondary_metrics": ["mae", "rmse", "r2"],
        "n_splits": n_splits,
        "primary_seed": primary_seed,
        "group": "user",
        "splitter": "GroupKFold",
        "shuffle": True,
        "shared_target_and_model_folds": True,
        "tuning": "none; fixed feature sets and ridge alpha",
        "feature_preprocessing": {
            "nonfinite": "replace positive/negative infinity with missing",
            "imputation": "training-fold median with missingness indicators",
            "all_missing_training_feature": "keep feature; impute zero as technical fallback",
            "scaling": "training-fold StandardScaler after imputation",
            "fit_scope": "training rows with finite target only, within each fold",
        },
        "target_policy": "exclude missing/nonfinite targets separately; never impute outcomes",
        "forbidden_predictors": [
            "both targets",
            "identifiers",
            "filenames",
            "unlisted measurements",
        ],
        "bootstrap": {
            "replicates": bootstrap_replicates,
            "seed": bootstrap_seed,
            "confidence_level": float(confidence_level),
            "method": "paired athlete-cluster percentile; NumPy linear quantiles",
            "unit": "athlete; every selected athlete retains all observed pitches and multiplicity",
            "scope": "conditional on fixed primary OOF errors; no pipeline refits",
            "comparisons": [list(pair) for pair in COMPARISONS],
            "multiplicity": "exploratory intervals; no p-values or multiplicity-adjusted claims",
        },
        "sensitivity": {
            "partition_seeds": list(seeds),
            "method": "full grouped refits, except reused identical primary seed",
            "interpretation": "partition sensitivity; not independent replications or confidence intervals",
        },
        **primary.feature_manifest,
    }
    return Phase2Results(
        primary.predictions,
        primary.metrics,
        primary.fold_metrics,
        primary.fold_assignments,
        primary.split_audit,
        athlete_error_table(primary.predictions),
        athlete_difference_table(primary.predictions),
        comparisons,
        bootstrap_samples,
        combined["predictions"],
        combined["metrics"],
        combined["fold_metrics"],
        combined["fold_assignments"],
        combined["athletes"],
        combined["athlete_differences"],
        combined["comparisons"],
        split_audit,
        specification,
    )


def save_phase2_results(results: Phase2Results, output_dir: str | Path) -> list[Path]:
    """Write Phase 2 artifacts without serializing fitted models."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    frames = {
        "oof_predictions": results.primary_predictions,
        "model_metrics": results.primary_metrics,
        "fold_metrics": results.primary_fold_metrics,
        "fold_assignments": results.primary_fold_assignments,
        "athlete_errors": results.athlete_errors,
        "athlete_differences": results.athlete_differences,
        "comparisons": results.comparisons,
        "bootstrap_samples": results.bootstrap_samples,
        "sensitivity_predictions": results.sensitivity_predictions,
        "sensitivity_metrics": results.sensitivity_metrics,
        "sensitivity_fold_metrics": results.sensitivity_fold_metrics,
        "sensitivity_fold_assignments": results.sensitivity_fold_assignments,
        "sensitivity_athlete_errors": results.sensitivity_athlete_errors,
        "sensitivity_athlete_differences": results.sensitivity_athlete_differences,
        "sensitivity_comparisons": results.sensitivity_comparisons,
    }
    written = []
    for name, frame in frames.items():
        if name in {"bootstrap_samples", "sensitivity_predictions"}:
            path = output / f"phase2_{name}.csv.gz"
            frame.to_csv(
                path,
                index=False,
                compression={"method": "gzip", "mtime": 0},
            )
        else:
            path = output / f"phase2_{name}.csv"
            frame.to_csv(path, index=False)
        written.append(path)
    for name, value in (
        ("split_audit", results.primary_split_audit),
        ("sensitivity_split_audit", results.sensitivity_split_audit),
        ("model_spec", results.specification),
    ):
        path = output / f"phase2_{name}.json"
        path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        written.append(path)
    return written
