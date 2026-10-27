"""Export the verified research brief without downloading data or fitting models."""

from __future__ import annotations

import argparse
from pathlib import Path

from pitching.research_brief import export_research_brief


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--reports-dir", type=Path, help="A completed local OBP reproduction")
    parser.add_argument("--output-dir", type=Path, required=True, help="A new output directory")
    args = parser.parse_args(argv)
    result = export_research_brief(args.project_dir, args.output_dir, args.reports_dir)
    print(f"Exported {len(result['files'])} verified research brief artifacts to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
