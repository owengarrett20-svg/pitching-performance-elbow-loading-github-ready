"""Reproduce the frozen Phase 2 plan and bind its outputs to the parent reports."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pitching.data import COMMIT
from pitching.models import FEATURES, RIDGE_ALPHA, TARGETS


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_phase2_plan(root: Path) -> tuple[dict[str, Any], bytes]:
    """Read the recorded specification; reject unsupported scientific settings.

    Runtime settings come from this file, rather than silently using a different
    default. A deliberate plan edit changes the recorded digest and requires a
    new interpretation of the study; it is not the previously frozen analysis.
    """
    from pitching.phase2 import COMPARISONS, FEATURE_SETS

    payload = (root / "analysis/phase2_plan.json").read_bytes()
    plan = json.loads(payload)
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise ValueError("Unsupported Phase 2 analysis plan schema")
    expected_groups = {
        "anthropometric": list(FEATURES[:3]),
        "kinematic": list(FEATURES[3:]),
        "combined": list(FEATURES),
    }
    if plan.get("source_commit") != COMMIT or plan.get("targets") != list(TARGETS):
        raise ValueError("Phase 2 plan must retain the pinned source and both targets")
    if plan.get("feature_sets") != expected_groups:
        raise ValueError("Phase 2 plan contains unsupported or forbidden predictor groups")
    expected_models = {
        "dummy_mean": {"estimator": "training_mean", "feature_set": None},
        **{
            f"ridge_{group}": {"estimator": "ridge", "feature_set": group}
            for group in expected_groups
        },
    }
    if plan.get("models") != expected_models or set(FEATURE_SETS) != set(expected_models):
        raise ValueError("Phase 2 plan and implemented models disagree")
    planned = plan.get("planned_comparisons", [])
    if not isinstance(planned, list) or any(not isinstance(item, dict) for item in planned):
        raise ValueError("Phase 2 planned comparisons must be a list of model/reference objects")
    if [(item.get("model"), item.get("reference")) for item in planned] != list(COMPARISONS):
        raise ValueError("Phase 2 plan must report every implemented paired comparison")
    primary = plan.get("primary_comparison", {})
    if (
        primary.get("model") != "ridge_combined"
        or primary.get("reference") != "ridge_anthropometric"
        or primary.get("difference") != "model_minus_reference"
        or primary.get("improvement_direction") != "negative"
        or plan.get("primary_metric") != "athlete_mae"
        or plan.get("secondary_metrics") != ["mae", "rmse", "r2"]
    ):
        raise ValueError("Unsupported Phase 2 primary estimand or comparison direction")
    if (
        plan.get("ridge_alpha") != RIDGE_ALPHA
        or plan.get("group_column") != "user"
        or plan.get("pitch_column") != "session_pitch"
    ):
        raise ValueError("Phase 2 requires fixed alpha and athlete-grouped evaluation")
    bootstrap = plan.get("bootstrap", {})
    if (
        bootstrap.get("method") != "paired_cluster_percentile"
        or bootstrap.get("unit") != "athlete"
        or bootstrap.get("scope") != "fixed_oof_predictions"
        or bootstrap.get("metrics") != ["athlete_mae", "mae"]
        or bootstrap.get("refit_within_resample") is not False
    ):
        raise ValueError("Unsupported Phase 2 bootstrap scope or resampling unit")
    level = bootstrap.get("confidence_level")
    if isinstance(level, bool) or not isinstance(level, (int, float)) or not 0 < level < 1:
        raise ValueError("Phase 2 confidence_level must be between zero and one")
    quantiles = [(1 - level) / 2, 1 - (1 - level) / 2]
    if not np.allclose(bootstrap.get("interval_quantiles", []), quantiles, atol=1e-12):
        raise ValueError("Phase 2 percentile quantiles disagree with confidence_level")
    integer_settings = {
        "n_splits": (plan.get("n_splits"), 2),
        "primary_seed": (plan.get("primary_seed"), 0),
        "bootstrap.n_resamples": (bootstrap.get("n_resamples"), 2),
        "bootstrap.seed": (bootstrap.get("seed"), 0),
    }
    for name, (value, minimum) in integer_settings.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"Phase 2 {name} must be an integer >= {minimum}")
    seeds = plan.get("sensitivity_seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seeds)
        or len(set(seeds)) != len(seeds)
        or plan["primary_seed"] not in seeds
    ):
        raise ValueError("Phase 2 sensitivity seeds must be unique and include the primary seed")
    inclusion = plan.get("inclusion", {})
    if inclusion.get("outlier_removal") is not False:
        raise ValueError("Phase 2 does not implement outlier removal")
    for field in ("expected_pitches", "expected_athletes"):
        value = inclusion.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"Phase 2 inclusion.{field} must be a positive integer")
    return plan, payload


def _check_phase1_reproduction(output: Path, result: Any) -> dict[str, Any]:
    """Require the unchanged mean/combined specification to reproduce Phase 1."""
    original = pd.read_csv(
        output / "oof_predictions.csv", dtype={"session_pitch": str, "user": str}
    )
    current = result.primary_predictions.copy()
    current = current[current["model"].isin(["dummy_mean", "ridge_combined"])].copy()
    current["model"] = current["model"].replace({"ridge_combined": "ridge"})
    keys = ["target", "model", "session_pitch"]
    original = original.sort_values(keys).reset_index(drop=True)
    current = current.sort_values(keys).reset_index(drop=True)
    identity = keys + ["user", "fold"]
    try:
        pd.testing.assert_frame_equal(original[identity], current[identity], check_dtype=False)
    except AssertionError as error:
        raise ValueError("Phase 2 model memberships or folds do not reproduce Phase 1") from error
    columns = ["observed", "predicted", "residual", "absolute_error"]
    first = original[columns].to_numpy(dtype=float)
    second = current[columns].to_numpy(dtype=float)
    if not np.allclose(first, second, rtol=1e-12, atol=1e-10):
        raise ValueError("Phase 2 mean/combined predictions do not reproduce Phase 1")
    return {
        "passed": True,
        "compared_rows": len(current),
        "max_absolute_difference": float(np.max(np.abs(first - second))),
        "tolerance": "rtol=1e-12, atol=1e-10",
    }


def run_phase2_workflow(root: Path, data_dir: Path, output: Path, offline: bool = False) -> dict:
    """Rebuild Phase 1, evaluate the recorded Phase 2 plan, and complete atomically.

    The parent completion marker binds every Phase 2 output and its own child
    metadata. A Phase-1-only refresh cannot silently display an older Phase 2
    study, and incomplete new results never acquire a completed parent binding.
    """
    from pitching.cli import run_workflow, write_json
    from pitching.phase2 import evaluate_phase2, save_phase2_results
    from pitching.phase2_reporting import write_phase2_report

    root, data_dir, output = Path(root).resolve(), Path(data_dir).resolve(), Path(output).resolve()
    plan, payload = load_phase2_plan(root)
    child = output / "phase2"
    child.mkdir(parents=True, exist_ok=True)
    (child / "run_metadata.json").unlink(missing_ok=True)
    phase1 = run_workflow(root, data_dir, output, plan["n_splits"], plan["primary_seed"], offline)
    analysis = pd.read_csv(
        output / "analysis.csv",
        dtype={"session_pitch": str, "user": str},
        float_precision="round_trip",
    )
    inclusion = plan["inclusion"]
    if (
        len(analysis) != inclusion["expected_pitches"]
        or analysis["user"].nunique() != inclusion["expected_athletes"]
    ):
        raise ValueError("Verified source composition does not match the frozen Phase 2 plan")
    bootstrap = plan["bootstrap"]
    result = evaluate_phase2(
        analysis,
        n_splits=plan["n_splits"],
        primary_seed=plan["primary_seed"],
        sensitivity_seeds=tuple(plan["sensitivity_seeds"]),
        bootstrap_replicates=bootstrap["n_resamples"],
        bootstrap_seed=bootstrap["seed"],
        confidence_level=bootstrap["confidence_level"],
    )
    reproduction = _check_phase1_reproduction(output, result)
    generated = list(save_phase2_results(result, child))
    plan_copy = child / "phase2_plan.json"
    plan_copy.write_bytes(payload)
    generated.append(plan_copy)
    attribution = child / "ATTRIBUTION.md"
    attribution.write_text(
        (output / "ATTRIBUTION.md").read_text()
        + "\nPhase 2 changes: fixed predictor-group comparisons, paired conditional "
        "athlete-cluster bootstrap intervals, and refitted partition-sensitivity analyses. "
        "No additional measured observations were created.\n",
        encoding="utf-8",
    )
    generated.append(attribution)
    generated.extend(write_phase2_report(child, plan))
    plan_revision = subprocess.run(
        ["git", "-C", str(root), "log", "-1", "--format=%H", "--", "analysis/phase2_plan.json"],
        capture_output=True,
        text=True,
        check=False,
    )
    files: dict[str, str] = {}
    for path in generated:
        if not path.resolve().is_relative_to(child) or path.is_symlink():
            raise ValueError("Phase 2 generated artifact is outside its report directory")
        files[path.relative_to(child).as_posix()] = _digest(path)
    metadata = {
        "status": "completed",
        "phase": "phase2",
        "source_commit": COMMIT,
        "completed_utc": datetime.now(UTC).isoformat(),
        "analysis_sha256": _digest(output / "analysis.csv"),
        "phase1_predictions_sha256": _digest(output / "oof_predictions.csv"),
        "plan_sha256": hashlib.sha256(payload).hexdigest(),
        "plan_path": "analysis/phase2_plan.json",
        "analysis_inputs_sha256": {
            "analysis/phase2_plan.json": hashlib.sha256(payload).hexdigest()
        },
        "plan_git_commit": plan_revision.stdout.strip() if plan_revision.returncode == 0 else None,
        "project_git_commit": phase1["project_git_commit"],
        "project_git_dirty": phase1["project_git_dirty"],
        "project_code_sha256": phase1["project_code_sha256"],
        "input_manifest_sha256": phase1["input_manifest_sha256"],
        "uv_lock_sha256": phase1["uv_lock_sha256"],
        "python": phase1["python"],
        "packages": phase1["packages"],
        "phase1_reproduction": reproduction,
        "primary_seed": plan["primary_seed"],
        "sensitivity_seeds": plan["sensitivity_seeds"],
        "bootstrap": bootstrap,
        "artifacts_sha256": files,
        "interpretation": plan["interpretation"],
        "data_terms": "See docs/LICENSING.md; derived outputs retain upstream restrictions.",
    }
    # Write the child marker first. It cannot be displayed until the completed
    # parent explicitly binds it and every child artifact, below.
    temporary = child / "run_metadata.json.tmp"
    write_json(temporary, metadata)
    temporary.replace(child / "run_metadata.json")
    phase1["artifacts_sha256"].update({f"phase2/{name}": value for name, value in files.items()})
    phase1["artifacts_sha256"]["phase2/run_metadata.json"] = _digest(child / "run_metadata.json")
    phase1["completed_phases"] = ["phase1", "phase2"]
    phase1["phase2_plan_sha256"] = metadata["plan_sha256"]
    phase1["analysis_inputs_sha256"] = metadata["analysis_inputs_sha256"]
    phase1["completed_utc"] = datetime.now(UTC).isoformat()
    temporary = output / "run_metadata.json.tmp"
    write_json(temporary, phase1)
    temporary.replace(output / "run_metadata.json")
    print(result.primary_metrics.to_string(index=False))
    print(f"Wrote verified Phase 1 + Phase 2 reports to {output}")
    return metadata
