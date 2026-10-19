"""Prepare three trace examples from checksum-verified canonical release archives."""

from pathlib import Path

from pitching.trace_examples import prepare_trace_examples

if __name__ == "__main__":
    manifest = prepare_trace_examples(Path(__file__).resolve().parents[1])
    for example in manifest["examples"]:
        print(example["session_pitch"], example["n_samples"], example["comparison"])
