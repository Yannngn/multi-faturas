"""Unit tests for the main CLI entry point."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.main import build_arg_parser, main


class TestArgParser:
    def test_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            parser = build_arg_parser()
            args = parser.parse_args([])
            assert args.root == Path(".")

    def test_custom_args(self):
        parser = build_arg_parser()
        args = parser.parse_args(["-r", "/tmp/root"])
        assert args.root == Path("/tmp/root")


class TestMain:
    def test_returns_1_when_no_output(self, tmp_path):
        result = main(["--root", str(tmp_path)])
        assert result == 1

    def test_returns_0_on_success(self, tmp_path):
        fake_path = tmp_path / "out.csv"
        with (
            patch("src.main.Extractor") as MockExtractor,
            patch("src.main.DataMerger") as MockDataMerger,
        ):
            MockExtractor.return_value.extract_all.return_value = [MagicMock()]
            MockDataMerger.return_value.consolidate.return_value = fake_path
            result = main(["--root", str(tmp_path)])
        assert result == 0
