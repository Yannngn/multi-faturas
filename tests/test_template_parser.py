"""Unit tests for TemplateBankParser helper methods."""

import pytest

from src.parsers.template_bank_parser import TemplateBankParser


@pytest.fixture
def parser(tmp_path):
    """Return a parser instance pointing at a temporary (non-existent) PDF."""
    return TemplateBankParser(str(tmp_path / "fake.pdf"))


class TestParseBrlValue:
    def test_simple_value(self, parser):
        assert parser._parse_brl_value("200,00") == 200.0

    def test_thousands_separator(self, parser):
        assert parser._parse_brl_value("1.234,56") == 1234.56

    def test_negative_value(self, parser):
        assert parser._parse_brl_value("-200,00") == -200.0

    def test_real_prefix(self, parser):
        assert parser._parse_brl_value("R$ 50,00") == 50.0

    def test_non_breaking_space(self, parser):
        assert parser._parse_brl_value("R\xa050,00") == 50.0

    def test_invalid_value_raises(self, parser):
        with pytest.raises(ValueError):
            parser._parse_brl_value("not-a-number")


class TestParseRow:
    def test_valid_row(self, parser):
        result = parser._parse_row(["15/06/2024", "Supermercado", "120,50"])
        assert result is not None
        assert result["Data"] == "15/06/2024"
        assert result["Banco/Origem"] == "Template Bank"
        assert result["Descrição da Transação"] == "Supermercado"
        assert result["Valor"] == 120.50
        assert result["Categoria"] == ""

    def test_row_too_short(self, parser):
        assert parser._parse_row(["15/06/2024", "Supermercado"]) is None

    def test_empty_row(self, parser):
        assert parser._parse_row([]) is None

    def test_invalid_date_returns_none(self, parser):
        assert parser._parse_row(["not-a-date", "Supermercado", "100,00"]) is None

    def test_invalid_value_returns_none(self, parser):
        assert parser._parse_row(["15/06/2024", "Supermercado", "abc"]) is None
