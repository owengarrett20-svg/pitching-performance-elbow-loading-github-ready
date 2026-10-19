"""Synthetic-only safeguards for ablation, clustering, and fixed-OOF inference."""

import json

import numpy as np
import pandas as pd
import pytest

from pitching.models import FEATURES, TARGETS, evaluate_baselines
from pitching.phase2 import (
    ANTHROPOMETRIC_FEATURES,
    COMPARISONS,
    FEATURE_SETS,
    KINEMATIC_FEATURES,
    compare_fixed_predictions,
    evaluate_phase2,
    save_phase2_results,
)


@pytest.fixture
def pitches():
    """Artificial data; these are never reported as OBP observations."""
    rng = np.random.default_rng(917)
    counts = np.tile([2, 3, 4], 4)
    n = sum(counts)
    frame = pd.DataFrame(
        {
            "session_pitch": [f"synthetic-{i}" for i in range(n)],
            "user": np.repeat([f"athlete-{i:02}" for i in range(12)], counts),
            "pitch_speed_mph": rng.normal(80, 5, n),
            "elbow_varus_moment": rng.normal(65, 15, n),
            **{name: rng.normal(size=n) for name in FEATURES},
        }
    )
    frame.loc[::7, FEATURES[0]] = np.nan
    return frame


@pytest.fixture
def result(pitches):
    return evaluate_phase2(
        pitches,
        n_splits=3,
        sensitivity_seeds=(42, 43),
        bootstrap_replicates=40,
        bootstrap_seed=172,
    )


@pytest.fixture
def known_predictions():
    """Unequal cluster sizes expose accidental pitch-level/equal-weight mixing."""
    parts = []
    counts = [1, 2, 4]
    errors = {
        "dummy_mean": [5, 5, 5],
        "ridge_anthropometric": [1, 3, 6],
        "ridge_kinematic": [3, 2, 4],
        "ridge_combined": [0.5, 1, 5],
    }
    for target in TARGETS:
        for model in FEATURE_SETS:
            for athlete, n in enumerate(counts):
                for pitch in range(n):
                    observed = 10.0 + pitch
                    error = errors[model][athlete]
                    parts.append(
                        {
                            "session_pitch": f"synthetic-{athlete}-{pitch}",
                            "user": f"athlete-{athlete}",
                            "fold": athlete + 1,
                            "target": target,
                            "model": model,
                            "observed": observed,
                            "predicted": observed - error,
                            "residual": error,
                            "absolute_error": error,
                        }
                    )
    return pd.DataFrame(parts)


def test_combined_and_mean_predictions_reproduce_phase1_exactly(pitches, result):
    phase1 = evaluate_baselines(pitches, n_splits=3, seed=42)
    pd.testing.assert_frame_equal(phase1.fold_assignments, result.primary_fold_assignments)
    for old, new in (("dummy_mean", "dummy_mean"), ("ridge", "ridge_combined")):
        before = phase1.predictions.loc[phase1.predictions.model.eq(old)].reset_index(drop=True)
        after = result.primary_predictions.loc[result.primary_predictions.model.eq(new)].copy()
        after["model"] = old
        pd.testing.assert_frame_equal(before, after.reset_index(drop=True), check_exact=True)


def test_every_seed_holds_athletes_out_and_shares_model_target_folds(pitches, result):
    for seed, assignments in result.sensitivity_fold_assignments.groupby("partition_seed"):
        assert len(assignments) == len(pitches)
        assert assignments.groupby("user").fold.nunique().eq(1).all()
        selected = result.sensitivity_predictions.query("partition_seed == @seed")
        assert selected.groupby("session_pitch").fold.nunique().eq(1).all()
        assert len(selected) == len(pitches) * len(TARGETS) * len(FEATURE_SETS)
    for partition in result.sensitivity_split_audit:
        for split in partition["folds"]:
            assert set(split["train_athletes"]).isdisjoint(split["test_athletes"])
            assert split["athlete_overlap"] == 0
    assert set(result.sensitivity_fold_metrics.partition_seed) == {42, 43}
    assert set(result.sensitivity_athlete_errors.partition_seed) == {42, 43}
    assert set(result.sensitivity_comparisons.partition_seed) == {42, 43}


@pytest.mark.parametrize(
    ("changed_features", "unaffected_model"),
    [
        (ANTHROPOMETRIC_FEATURES, "ridge_kinematic"),
        (KINEMATIC_FEATURES, "ridge_anthropometric"),
    ],
)
def test_feature_ablations_use_only_their_allowlist(
    pitches, result, changed_features, unaffected_model
):
    changed = pitches.copy()
    for feature in changed_features:
        changed[feature] = np.arange(len(changed)) + 1e8
    altered = evaluate_phase2(changed, n_splits=3, sensitivity_seeds=(42,), bootstrap_replicates=10)
    before = result.primary_predictions.query("model == @unaffected_model").predicted
    after = altered.primary_predictions.query("model == @unaffected_model").predicted
    np.testing.assert_array_equal(before, after)


def test_preprocessing_cannot_use_other_heldout_values(pitches, result):
    heldout = result.primary_fold_assignments.query("fold == 1").session_pitch.tolist()
    focus, outlier = heldout[:2]
    reference = pitches.copy()
    reference.loc[reference.session_pitch.eq(focus), list(FEATURES)] = np.nan
    changed = reference.copy()
    changed.loc[changed.session_pitch.eq(outlier), list(FEATURES)] = 1e12
    kwargs = {"n_splits": 3, "sensitivity_seeds": (42,), "bootstrap_replicates": 10}
    first = evaluate_phase2(reference, **kwargs).primary_predictions
    second = evaluate_phase2(changed, **kwargs).primary_predictions
    np.testing.assert_array_equal(
        first.query("session_pitch == @focus").predicted,
        second.query("session_pitch == @focus").predicted,
    )


def test_other_outcome_identifiers_and_speed_filenames_are_not_predictors(pitches, result):
    changed = pitches.copy()
    changed[TARGETS[1]] = changed[TARGETS[0]] * 100
    changed["pitch_speed_mph_metadata"] = changed[TARGETS[0]]
    changed["filename"] = changed[TARGETS[0]].map(lambda speed: f"{speed}.c3d")
    altered = evaluate_phase2(changed, n_splits=3, sensitivity_seeds=(42,), bootstrap_replicates=10)
    np.testing.assert_array_equal(
        result.primary_predictions.query("target == 'pitch_speed_mph'").predicted,
        altered.primary_predictions.query("target == 'pitch_speed_mph'").predicted,
    )
    for features in FEATURE_SETS.values():
        assert not set(features) & {"user", "session_pitch", "filename", *TARGETS}


def test_missing_outcomes_never_imputed_and_all_model_pairs_match(pitches):
    data = pitches.copy()
    data.loc[0, TARGETS[0]] = np.nan
    data.loc[1, TARGETS[1]] = np.inf
    data[FEATURES[1]] = np.nan
    data.loc[2, FEATURES[2]] = np.inf
    data.index = np.zeros(len(data), dtype=int)
    result = evaluate_phase2(data, n_splits=3, sensitivity_seeds=(42,), bootstrap_replicates=10)
    for target in TARGETS:
        valid = np.isfinite(data[target])
        for model in FEATURE_SETS:
            selected = result.primary_predictions.query("target == @target and model == @model")
            assert set(selected.session_pitch) == set(data.loc[valid, "session_pitch"])
    assert np.isfinite(result.primary_predictions.predicted).all()
    assert result.specification["excluded_target_rows"] == dict.fromkeys(TARGETS, 1)
    assert result.specification["nonfinite_feature_counts"][FEATURES[2]] == 1


def test_dummy_is_training_mean_and_metrics_match_saved_errors(pitches, result):
    assignments = result.primary_fold_assignments.set_index("session_pitch").fold
    for row in result.primary_metrics.itertuples():
        selected = result.primary_predictions.query("target == @row.target and model == @row.model")
        assert row.athlete_mae == pytest.approx(
            selected.groupby("user").absolute_error.mean().mean()
        )
        assert row.mae == pytest.approx(selected.absolute_error.mean())
        assert row.rmse == pytest.approx(np.sqrt(np.mean(selected.residual**2)))
        for fold, heldout in selected.groupby("fold"):
            if row.model == "dummy_mean":
                expected = pitches.loc[
                    pitches.session_pitch.map(assignments).ne(fold), row.target
                ].mean()
                np.testing.assert_allclose(heldout.predicted, expected)
    for row in result.athlete_errors.itertuples():
        selected = result.primary_predictions.query(
            "target == @row.target and model == @row.model and user == @row.user"
        )
        assert row.mae == pytest.approx(selected.absolute_error.mean())
        assert row.bias == pytest.approx(selected.residual.mean())
        assert row.rmse == pytest.approx(np.sqrt(np.mean(selected.residual**2)))


def test_bootstrap_exactly_retains_paired_cluster_multiplicity(known_predictions):
    replicates, seed = 100, 913
    contrasts, samples = compare_fixed_predictions(
        known_predictions, bootstrap_replicates=replicates, bootstrap_seed=seed
    )
    difference = np.array([-0.5, -2.0, -1.0])
    counts = np.array([1, 2, 4])
    rng = np.random.default_rng(seed)
    for target in TARGETS:
        draws = rng.integers(0, 3, size=(replicates, 3))
        expected = {
            "athlete_mae": difference[draws].mean(axis=1),
            "mae": (difference * counts)[draws].sum(axis=1) / counts[draws].sum(axis=1),
        }
        for metric, values in expected.items():
            selector = (
                "target == @target and model == 'ridge_combined' "
                "and reference == 'ridge_anthropometric' and metric == @metric"
            )
            row = contrasts.query(selector).iloc[0]
            actual = samples.query(selector).difference.to_numpy()
            np.testing.assert_allclose(actual, values, rtol=0, atol=1e-14)
            assert row.ci_low == pytest.approx(np.quantile(values, 0.025))
            assert row.ci_high == pytest.approx(np.quantile(values, 0.975))
            point = (
                difference.mean()
                if metric == "athlete_mae"
                else np.average(difference, weights=counts)
            )
            assert row.estimate == pytest.approx(point)
            assert row.n_pitches == 7
            assert row.n_athletes == 3
    assert len(contrasts) == len(TARGETS) * len(COMPARISONS) * 2
    assert contrasts.primary.sum() == len(TARGETS)


def test_bootstrap_is_reproducible_and_ignores_prediction_row_order(known_predictions):
    kwargs = {"bootstrap_replicates": 300, "bootstrap_seed": 47}
    first = compare_fixed_predictions(known_predictions, **kwargs)
    second = compare_fixed_predictions(known_predictions.sample(frac=1, random_state=8), **kwargs)
    for before, after in zip(first, second, strict=True):
        pd.testing.assert_frame_equal(before, after)


@pytest.mark.parametrize(
    "damage", ["missing", "duplicate", "observed", "user", "fold", "zero_fold", "error", "infinite"]
)
def test_pairing_rejects_misaligned_or_invalid_comparisons(known_predictions, damage):
    data = known_predictions.copy()
    idx = data.query("model == 'ridge_combined'").index[0]
    if damage == "missing":
        data = data.drop(index=idx)
    elif damage == "duplicate":
        data = pd.concat([data, data.loc[[idx]]], ignore_index=True)
    elif damage == "observed":
        data.loc[idx, "observed"] += 1
        data.loc[idx, "absolute_error"] = abs(
            data.loc[idx, "observed"] - data.loc[idx, "predicted"]
        )
    elif damage == "user":
        data.loc[idx, "user"] = "other-athlete"
    elif damage == "fold":
        data.loc[idx, "fold"] = 99
    elif damage == "zero_fold":
        data["fold"] = 0
    elif damage == "error":
        data.loc[idx, "absolute_error"] += 1
    else:
        data.loc[idx, "predicted"] = np.inf
    with pytest.raises(ValueError):
        compare_fixed_predictions(data, bootstrap_replicates=10)


def test_athlete_differences_reconstruct_all_primary_estimates(result):
    for row in result.comparisons.query("metric == 'athlete_mae'").itertuples():
        selected = result.athlete_differences.query(
            "target == @row.target and model == @row.model and reference == @row.reference"
        )
        assert selected.mae_difference.mean() == pytest.approx(row.estimate)
    for seed in (42, 43):
        selected = result.sensitivity_athlete_differences.query("partition_seed == @seed")
        assert len(selected) == 12 * len(TARGETS) * len(COMPARISONS)


def test_constant_outcomes_keep_r2_undefined_and_zero_error(pitches):
    data = pitches.copy()
    data[list(TARGETS)] = 10.0
    result = evaluate_phase2(data, n_splits=3, sensitivity_seeds=(42,), bootstrap_replicates=10)
    assert result.primary_metrics.r2.isna().all()
    np.testing.assert_allclose(result.primary_metrics.mae, 0)
    np.testing.assert_allclose(result.comparisons[["estimate", "ci_low", "ci_high"]], 0)


def test_unobserved_training_target_and_duplicate_pitch_rejected(pitches):
    duplicated = pd.concat([pitches, pitches.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="one pitch per row"):
        evaluate_phase2(duplicated, n_splits=3, sensitivity_seeds=(42,), bootstrap_replicates=10)
    data = pitches.copy()
    data[TARGETS[0]] = np.nan
    with pytest.raises(ValueError, match="No finite observed target"):
        evaluate_phase2(data, n_splits=3, sensitivity_seeds=(42,), bootstrap_replicates=10)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"n_splits": True},
        {"n_splits": 20},
        {"sensitivity_seeds": ()},
        {"sensitivity_seeds": (42, 42)},
        {"sensitivity_seeds": (True,)},
        {"bootstrap_replicates": 1},
        {"bootstrap_seed": -1},
        {"confidence_level": 1},
        {"confidence_level": np.nan},
    ],
)
def test_invalid_configuration_fails_before_fitting(pitches, kwargs):
    with pytest.raises((ValueError, TypeError)):
        evaluate_phase2(pitches, **kwargs)


def test_saved_files_are_explicit_and_gzip_bytes_are_deterministic(result, tmp_path):
    one = tmp_path / "one"
    two = tmp_path / "two"
    one.mkdir()
    unmanaged = one / "not-an-artifact.txt"
    unmanaged.write_text("unrelated", encoding="utf-8")
    first = save_phase2_results(result, one)
    second = save_phase2_results(result, two)
    assert unmanaged not in first
    assert len(first) == 18
    assert {path.name for path in first} == {path.name for path in second}
    for before, after in zip(first, second, strict=True):
        assert before.read_bytes() == after.read_bytes()
    samples = pd.read_csv(one / "phase2_bootstrap_samples.csv.gz")
    assert len(samples) == len(result.bootstrap_samples)
    assert "partition_seed" in pd.read_csv(one / "phase2_sensitivity_predictions.csv.gz")
    spec = json.loads((one / "phase2_model_spec.json").read_text())
    assert (
        spec["bootstrap"]["scope"] == "conditional on fixed primary OOF errors; no pipeline refits"
    )
    assert spec["primary_metric"] == "athlete_mae"
    assert spec["sensitivity"]["partition_seeds"] == [42, 43]
