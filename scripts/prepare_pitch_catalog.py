"""Prepare a source-verified measured-marker catalog without downloading anything."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pitching.pitch_catalog import prepare_pitch_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--archive", type=Path, required=True, help="Existing verified pitching_c3d.zip"
    )
    parser.add_argument(
        "--output-dir", type=Path, help="New catalog directory; default assets/pitch_catalog"
    )
    args = parser.parse_args()
    try:
        manifest = prepare_pitch_catalog(args.project_dir, args.archive, args.output_dir)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Catalog preparation stopped: {error}\n")
    print(json.dumps(manifest["quality_summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
