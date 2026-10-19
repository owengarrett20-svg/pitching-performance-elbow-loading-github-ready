"""Export real, completed pipeline reports for a read-only hosted dashboard."""

from __future__ import annotations

import argparse
from pathlib import Path

from pitching.deployment import export_demo_snapshot, verified_demo_reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--reports-dir", type=Path, help="Completed local pipeline reports")
    args = parser.parse_args()
    manifest = export_demo_snapshot(args.project_dir, args.reports_dir)
    reports = verified_demo_reports(args.project_dir)
    print(f"Exported and verified {len(manifest['files'])} reference artifacts: {reports}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
