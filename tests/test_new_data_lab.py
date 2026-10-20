"""The public planning kit must never package an operator's private study."""

import io
import zipfile

import pytest

from pitching.new_data_lab import TEMPLATE_PATHS, planning_files, planning_zip


def test_planning_kit_contains_only_fixed_templates_and_is_reproducible(tmp_path):
    for relative in TEMPLATE_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"template": true}' if path.suffix == ".json" else "field,unit\n")
    private = tmp_path / "local_studies" / "private.csv"
    private.parent.mkdir()
    private.write_text("NEVER PACKAGE PRIVATE RECORDS")
    expected = {relative.split("/")[-1] for relative in TEMPLATE_PATHS} | {"START_HERE.txt"}
    first = planning_zip(tmp_path)
    assert first == planning_zip(tmp_path)
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert set(archive.namelist()) == expected
        assert all(b"NEVER PACKAGE" not in archive.read(name) for name in archive.namelist())
        assert b"blank planning templates" in archive.read("START_HERE.txt")


def test_missing_or_malformed_planning_templates_fail_instead_of_showing_study_ready(tmp_path):
    with pytest.raises(FileNotFoundError):
        planning_files(tmp_path)
    path = tmp_path / TEMPLATE_PATHS[0]
    path.parent.mkdir(parents=True)
    path.write_text("[]")
    with pytest.raises(ValueError, match="JSON object"):
        planning_files(tmp_path)
