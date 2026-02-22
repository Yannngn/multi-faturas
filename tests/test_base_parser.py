"""Unit tests for BaseParser schema validation."""

import pandas as pd
import pytest

from src.parsers.base_parser import REQUIRED_COLUMNS, BaseParser


class ConcreteParser(BaseParser):
    """Minimal concrete parser used only for testing the base class."""

    bank_name = "TestBank"

    def parse(self) -> pd.DataFrame:
        return self._build_empty_dataframe()


class TestRequiredColumns:
    def test_required_columns_defined(self):
        assert REQUIRED_COLUMNS == [
            "Data",
            "Banco/Origem",
            "Descrição da Transação",
            "Valor",
            "Categoria",
        ]


class TestBaseParserInstantiation:
    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            BaseParser("some/path.pdf")

    def test_concrete_parser_instantiates(self):
        parser = ConcreteParser("some/path.pdf")
        assert parser.source_path == "some/path.pdf"
        assert parser.bank_name == "TestBank"


class TestBuildEmptyDataFrame:
    def test_returns_empty_dataframe_with_correct_columns(self):
        parser = ConcreteParser("some/path.pdf")
        df = parser._build_empty_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == REQUIRED_COLUMNS
        assert len(df) == 0


class TestValidateDataFrame:
    def test_validates_complete_dataframe(self):
        parser = ConcreteParser("some/path.pdf")
        data = {col: ["value"] for col in REQUIRED_COLUMNS}
        df = pd.DataFrame(data)
        validated = parser._validate_dataframe(df)
        assert list(validated.columns) == REQUIRED_COLUMNS

    def test_fills_missing_columns(self):
        parser = ConcreteParser("some/path.pdf")
        df = pd.DataFrame({"Data": ["01/01/2024"]})
        validated = parser._validate_dataframe(df)
        assert list(validated.columns) == REQUIRED_COLUMNS
        assert validated["Valor"].iloc[0] is None

    def test_reorders_extra_columns(self):
        parser = ConcreteParser("some/path.pdf")
        data = {col: ["x"] for col in reversed(REQUIRED_COLUMNS)}
        df = pd.DataFrame(data)
        validated = parser._validate_dataframe(df)
        assert list(validated.columns) == REQUIRED_COLUMNS
