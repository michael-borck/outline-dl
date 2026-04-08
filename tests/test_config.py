"""Tests for config module."""

from pathlib import Path

import pytest

from outline_dl.config import resolve_unit_codes, validate_unit_code


class TestValidateUnitCode:
    def test_valid_code(self) -> None:
        assert validate_unit_code("COMP1000") == "COMP1000"

    def test_lowercase_normalized(self) -> None:
        assert validate_unit_code("comp1000") == "COMP1000"

    def test_mixed_case(self) -> None:
        assert validate_unit_code("Comp1000") == "COMP1000"

    def test_with_whitespace(self) -> None:
        assert validate_unit_code("  COMP1000  ") == "COMP1000"

    def test_invalid_too_short(self) -> None:
        with pytest.raises(ValueError, match="Invalid unit code"):
            validate_unit_code("COM100")

    def test_invalid_wrong_format(self) -> None:
        with pytest.raises(ValueError, match="Invalid unit code"):
            validate_unit_code("1000COMP")

    def test_invalid_empty(self) -> None:
        with pytest.raises(ValueError, match="Invalid unit code"):
            validate_unit_code("")


class TestResolveUnitCodes:
    def test_from_cli_args(self) -> None:
        codes = resolve_unit_codes(["COMP1000", "ISAD1000"])
        assert codes == ["COMP1000", "ISAD1000"]

    def test_from_file(self, tmp_path: Path) -> None:
        f = tmp_path / "units.txt"
        f.write_text("COMP1000\nISAD1000\n")
        codes = resolve_unit_codes(file_path=f)
        assert codes == ["COMP1000", "ISAD1000"]

    def test_from_file_comma_separated(self, tmp_path: Path) -> None:
        f = tmp_path / "units.txt"
        f.write_text("COMP1000,ISAD1000,MATH1000")
        codes = resolve_unit_codes(file_path=f)
        assert codes == ["COMP1000", "ISAD1000", "MATH1000"]

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit, match="file not found"):
            resolve_unit_codes(file_path=tmp_path / "nope.txt")
