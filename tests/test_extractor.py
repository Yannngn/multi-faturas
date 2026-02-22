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
def root_dir(tmp_path):
    return tmp_path


class TestExtractorNoPdfs:
    def test_returns_empty_list_when_no_pdfs(self, root_dir):
        extractor = Extractor(root_dir=root_dir, parser_registry={})
        assert extractor.extract_all() == []


class TestExtractorResolvesParser:
    def test_unknown_file_is_skipped(self, root_dir):
        unknown_dir = root_dir / "unknown"
        unknown_dir.mkdir()
        (unknown_dir / "statement.pdf").touch()
        extractor = Extractor(
            root_dir=root_dir,
            parser_registry={"fake": FakeParser},
            bank_aliases={"fake": "fake"},
        )
        frames = extractor.extract_all()
        assert frames == []

    def test_known_file_is_parsed(self, root_dir):
        bank_dir = root_dir / "Fake_Bank"
        bank_dir.mkdir()
        pdf_path = bank_dir / "jan2024.pdf"
        pdf_path.touch()

        with patch.object(
            FakeParser,
            "parse",
            return_value=pd.DataFrame(
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
            ),
        ):
            extractor = Extractor(
                root_dir=root_dir,
                parser_registry={"fake": FakeParser},
                bank_aliases={"fake_bank": "fake"},
            )
            frames = extractor.extract_all()

        assert len(frames) == 1
        assert len(frames[0]) == 1

    def test_failing_parser_is_logged_and_skipped(self, root_dir, caplog):
        bank_dir = root_dir / "FailBank"
        bank_dir.mkdir()
        pdf_path = bank_dir / "jan2024.pdf"
        pdf_path.touch()
        extractor = Extractor(
            root_dir=root_dir,
            parser_registry={"fail": FailingParser},
            bank_aliases={"failbank": "fail"},
        )
        frames = extractor.extract_all()
        assert frames == []
        assert "Unrecognised layout" in caplog.text
