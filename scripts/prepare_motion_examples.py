"""Rebuild the bundled C3D motion replays from the checksum-verified OBP archive.

Run from the project root:
    uv run --extra motion python scripts/prepare_motion_examples.py

This command needs native ffmpeg and the already downloaded pitching_c3d.zip in
data/visual-source/. It does not fetch video footage or fit a biomechanics model.
"""

from pathlib import Path

from pitching.motion_examples import prepare_examples

if __name__ == "__main__":
    manifest = prepare_examples(Path(__file__).resolve().parents[1])
    print(f"Wrote {len(manifest['examples'])} licensed recorded-marker replays to assets/motion/")
