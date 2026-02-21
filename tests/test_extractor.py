"""Unit tests for the Extractor."""

from unittest.mock import patch

import pandas as pd
import pytest

from src.extractor import Extractor
from src.parsers.base_parser import REQUIRED_COLUMNS, BaseParser


class FakeParser(BaseParser):
    bank_name = "FakeBank"

    def parse(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "Data": "01/01/2024",
                    "Banco/Origem": "FakeBank",
                    "Descrição da Transação": "Test",
                    "Valor": 100.0,
                    "Categoria": "",
                }
            ],
            columns=REQUIRED_COLUMNS,
        )


class FailingParser(BaseParser):
    bank_name = "FailBank"

    def parse(self) -> pd.DataFrame:
        raise ValueError("Unrecognised layout")


@pytest.fixture
def input_dir(tmp_path):
    return tmp_path / "input"


class TestExtractorNoPdfs:
    def test_returns_empty_list_when_no_pdfs(self, input_dir):
        input_dir.mkdir()
        extractor = Extractor(input_dir=input_dir, parser_registry={})
        assert extractor.extract_all() == []


class TestExtractorResolvesParser:
    def test_unknown_file_is_skipped(self, input_dir):
        input_dir.mkdir()
        (input_dir / "unknown_bank_statement.pdf").touch()
        extractor = Extractor(input_dir=input_dir, parser_registry={"fakebank": FakeParser})
        frames = extractor.extract_all()
        assert frames == []

    def test_known_file_is_parsed(self, input_dir):
        input_dir.mkdir()
        pdf_path = input_dir / "fakebank_jan2024.pdf"
        pdf_path.touch()

        with patch.object(FakeParser, "parse", return_value=pd.DataFrame(
            [
                {
                    "Data": "01/01/2024",
                    "Banco/Origem": "FakeBank",
                    "Descrição da Transação": "Test",
                    "Valor": 100.0,
                    "Categoria": "",
                }
            ],
            columns=REQUIRED_COLUMNS,
        )):
            extractor = Extractor(input_dir=input_dir, parser_registry={"fakebank": FakeParser})
            frames = extractor.extract_all()

        assert len(frames) == 1
        assert len(frames[0]) == 1

    def test_failing_parser_is_logged_and_skipped(self, input_dir):
        input_dir.mkdir()
        pdf_path = input_dir / "failbank_jan2024.pdf"
        pdf_path.touch()
        extractor = Extractor(input_dir=input_dir, parser_registry={"failbank": FailingParser})
        frames = extractor.extract_all()
        assert frames == []
