"""One small, auditable Phase 1 workflow, usable without Jupyter."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from pitching.data import (
    COMMIT,
    DataValidationError,
    audit_dataset,
    fetch_source,
    verify_source,
)
from pitching.models import evaluate_baselines, save_model_results
from pitching.plots import descriptive_summary, error_plots, exploratory_plots


def write_json(path: Path, content: dict | list) -> None:
    path.write_text(json.dumps(content, indent=2, allow_nan=False) + "\n")


def _write_audit(root: Path, data_dir: Path, output: Path) -> pd.DataFrame:
    verified = verify_source(root / "source_manifest.json", data_dir)
    output.mkdir(parents=True, exist_ok=True)
    try:
        analysis, audit, missingness = audit_dataset(data_dir)
    except DataValidationError as exc:
        write_json(
            output / "audit.json",
            {"source": verified, **exc.report, "status": "failed", "error": str(exc)},
        )
        raise
    audit["source"] = verified
    write_json(output / "audit.json", audit)
    missingness.to_csv(output / "missingness.csv", index=False)
    analysis.to_csv(output / "analysis.csv", index=False)
    descriptive_summary(analysis).to_csv(output / "descriptive_summary.csv", index=False)
    missing = missingness.query("table == 'poi' and n_missing > 0")
    text = (
        "# Data audit\n\n"
        f"Source revision: `{COMMIT}`.\n\n"
        f"POI: {audit['poi']['n_rows']} rows; metadata: {audit['metadata']['n_rows']} rows. "
        f"Join: **one to one**, {len(analysis)} matched pitches, "
        f"{audit['n_athletes']} athletes, {audit['n_sessions']} sessions. "
        "No unmatched or duplicate pitch IDs. Shared sessions and observed pitch speeds agree.\n\n"
        f"{len(missing)} POI columns have missing observations. "
        "See missingness.csv for every column in each source table and the merged table; "
        "missing values remain missing.\n\n"
        "One row is a pitch, not an independent athlete. Hip–shoulder separation is a peak "
        "angle, not specifically the foot-plant angle. Elbow varus moment is an internal net "
        "moment, not tissue-specific ligament loading or an injury endpoint.\n\n"
        "Source: Driveline Baseball Research & Development, OpenBiomechanics Project. "
        "Data-derived outputs: upstream CC BY-NC-SA 4.0 with its additional "
        "professional-organization exclusion; see docs/LICENSING.md. "
        "This report joins and summarizes the original source tables.\n"
    )
    (output / "audit.md").write_text(text)
    print(f"Audit passed: {len(analysis)} pitches; {audit['n_athletes']} athletes; 1:1 join.")
    return analysis


def run_workflow(
    root: Path,
    data_dir: Path,
    output: Path,
    n_splits: int = 5,
    seed: int = 42,
    offline: bool = False,
) -> dict:
    if not offline:
        fetch_source(root / "source_manifest.json", data_dir)
    # Remove our completion marker before beginning a refresh: a failed run must
    # never leave a previous success marker beside partially refreshed results.
    output.mkdir(parents=True, exist_ok=True)
    (output / "run_metadata.json").unlink(missing_ok=True)
    analysis = _write_audit(root, data_dir, output)
    exploratory_plots(analysis, output / "figures")
    results = evaluate_baselines(analysis, n_splits=n_splits, seed=seed)
    save_model_results(results, output)
    error_plots(results.predictions, output / "figures")
    (output / "ATTRIBUTION.md").write_text(
        "# Data-derived reports\n\n"
        "Source: Driveline Baseball Research & Development, The OpenBiomechanics Project.\n\n"
        f"https://github.com/drivelineresearch/openbiomechanics/tree/{COMMIT}\n\n"
        "Changes: joined trial metadata, summarized observations, plotted measurements, "
        "and computed athlete-held-out baseline predictions. Raw observations were not filled.\n\n"
        "These outputs retain CC BY-NC-SA 4.0 with the additional upstream "
        "professional-sports/financial-analysis organization exclusion. "
        f"Full terms: https://github.com/drivelineresearch/openbiomechanics/blob/{COMMIT}/LICENSE-DATA.md\n\n"
        "Keep this attribution and license notice with redistributed figures, tables, and reports.\n"
    )
    packages = {
        name: importlib.metadata.version(name)
        for name in ("numpy", "pandas", "scikit-learn", "matplotlib", "streamlit")
    }
    artifacts = [
        "analysis.csv",
        "audit.json",
        "missingness.csv",
        "descriptive_summary.csv",
        "oof_predictions.csv",
        "model_metrics.csv",
        "fold_metrics.csv",
        "fold_assignments.csv",
        "split_audit.json",
        "model_spec.json",
    ]
    artifacts.extend(
        path.relative_to(output).as_posix() for path in sorted((output / "figures").glob("*.png"))
    )
    code_paths = sorted((root / "src").rglob("*.py")) + [root / "app.py", root / "pyproject.toml"]
    if (root / "streamlit_app.py").is_file():
        code_paths.append(root / "streamlit_app.py")
    revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    worktree = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    metadata = {
        "status": "completed",
        "source_commit": COMMIT,
        "completed_utc": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "packages": packages,
        "project_git_commit": revision.stdout.strip() if revision.returncode == 0 else None,
        "project_git_dirty": bool(worktree.stdout.strip()) if worktree.returncode == 0 else None,
        "project_code_sha256": {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in code_paths
        },
        "seed": seed,
        "n_splits": n_splits,
        "input_manifest_sha256": hashlib.sha256(
            (root / "source_manifest.json").read_bytes()
        ).hexdigest(),
        "uv_lock_sha256": hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
        "artifacts_sha256": {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in artifacts
        },
        "interpretation": "Retrospective athlete-held-out prediction; no injury or causal claims.",
        "data_terms": "See docs/LICENSING.md; data-derived outputs retain upstream restrictions.",
    }
    write_json(output / "run_metadata.json", metadata)
    print(results.metrics.to_string(index=False))
    print(f"Wrote verified Phase 1 reports to {output}")
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pitching Performance and Elbow Loading, Phase 1")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project root containing source_manifest.json (default: current directory)",
    )
    parser.add_argument(
        "--data-dir", type=Path, help="Verified source cache (default: PROJECT/data/raw)"
    )
    parser.add_argument(
        "--output-dir", type=Path, help="Generated reports (default: PROJECT/reports)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("fetch", help="Fetch and SHA-256 verify the pinned small CSV/docs files")
    subparsers.add_parser("audit", help="Offline schema, join, and missingness audit")
    run = subparsers.add_parser(
        "run", help="Fetch if needed, audit, plot, evaluate grouped baselines"
    )
    run.add_argument(
        "--offline", action="store_true", help="Verify local cache without network access"
    )
    run.add_argument("--folds", type=int, default=5)
    run.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    root = args.project_dir.resolve()
    data_dir = args.data_dir.resolve() if args.data_dir else root / "data/raw"
    output = args.output_dir.resolve() if args.output_dir else root / "reports"
    try:
        if args.command == "fetch":
            source = fetch_source(root / "source_manifest.json", data_dir)
            print(f"Verified {len(source['files'])} files at OBP {COMMIT} in {data_dir}")
        elif args.command == "audit":
            _write_audit(root, data_dir, output)
        else:
            run_workflow(root, data_dir, output, args.folds, args.seed, args.offline)
    except (DataValidationError, ValueError, OSError) as exc:
        print(f"Phase 1 stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
