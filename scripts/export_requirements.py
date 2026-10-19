"""Export a deterministic pip fallback from uv.lock, including the local package.

Run `uv run python scripts/export_requirements.py`; use --check in CI. uv.lock
remains authoritative. This script never resolves or updates dependency versions.
"""

import subprocess
import sys
from pathlib import Path


def exported_requirements(root: Path) -> str:
    result = subprocess.run(
        [
            "uv",
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--no-hashes",
            "--format",
            "requirements.txt",
            "--no-header",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return (
        "# Generated from uv.lock by scripts/export_requirements.py; do not edit by hand.\n"
        "# Runtime-only pip fallback; uv.lock is the authoritative analysis environment.\n"
        + result.stdout.strip()
        + "\n\n# Install the local src/pitching package.\n-e .\n"
    )


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    expected = exported_requirements(root)
    output = root / "requirements.txt"
    if "--check" in sys.argv:
        if not output.is_file() or output.read_text() != expected:
            raise SystemExit("requirements.txt differs from uv.lock; rerun this exporter.")
        print("requirements.txt matches the locked runtime dependencies.")
    else:
        output.write_text(expected)
        print(f"Wrote {output}")
