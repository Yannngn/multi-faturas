"""Unit tests for the main CLI entry point."""

from unittest.mock import MagicMock, patch
from pathlib import Path

from src.main import build_arg_parser, main


class TestArgParser:
    def test_defaults(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.input == Path("data/input")
        assert args.output == Path("data/output")
        assert args.filename == "faturas_consolidadas.csv"

    def test_custom_args(self):
        parser = build_arg_parser()
        args = parser.parse_args(["-i", "/tmp/in", "-o", "/tmp/out", "-f", "out.csv"])
        assert args.input == Path("/tmp/in")
        assert args.output == Path("/tmp/out")
        assert args.filename == "out.csv"


class TestMain:
    def test_returns_1_when_no_output(self, tmp_path):
        empty_input = tmp_path / "input"
        empty_input.mkdir()
        output = tmp_path / "output"
        result = main(["--input", str(empty_input), "--output", str(output)])
        assert result == 1

    def test_returns_0_on_success(self, tmp_path):
        fake_path = tmp_path / "out.csv"
        with (
            patch("src.main.Extractor") as MockExtractor,
            patch("src.main.Consolidator") as MockConsolidator,
        ):
            MockExtractor.return_value.extract_all.return_value = [MagicMock()]
            MockConsolidator.return_value.consolidate.return_value = fake_path
            result = main(["--input", str(tmp_path), "--output", str(tmp_path)])
        assert result == 0
