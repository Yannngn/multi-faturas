"""Unit tests for the Consolidator."""

import pandas as pd
import pytest

from src.parsers.base_parser import REQUIRED_COLUMNS
from src.consolidator import Consolidator


def make_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


@pytest.fixture
def output_dir(tmp_path):
    return tmp_path / "output"


class TestConsolidatorNoData:
    def test_returns_none_when_no_frames(self, output_dir):
        c = Consolidator(output_dir=output_dir)
        assert c.consolidate([]) is None


class TestConsolidatorWithData:
    def test_creates_csv(self, output_dir):
        frames = [
            make_frame([
                {
                    "Data": "10/01/2024",
                    "Banco/Origem": "TestBank",
                    "Descrição da Transação": "Café",
                    "Valor": 5.50,
                    "Categoria": "",
                }
            ])
        ]
        c = Consolidator(output_dir=output_dir)
        path = c.consolidate(frames)
        assert path is not None
        assert path.exists()
        df = pd.read_csv(path, encoding="utf-8-sig")
        assert list(df.columns) == REQUIRED_COLUMNS
        assert len(df) == 1

    def test_merges_multiple_frames(self, output_dir):
        row = {
            "Data": "01/02/2024",
            "Banco/Origem": "BankA",
            "Descrição da Transação": "Item",
            "Valor": 10.0,
            "Categoria": "",
        }
        frames = [make_frame([row]), make_frame([row])]
        c = Consolidator(output_dir=output_dir)
        path = c.consolidate(frames)
        df = pd.read_csv(path, encoding="utf-8-sig")
        assert len(df) == 2

    def test_sorted_by_date(self, output_dir):
        frames = [
            make_frame([
                {
                    "Data": "15/03/2024",
                    "Banco/Origem": "B",
                    "Descrição da Transação": "Later",
                    "Valor": 1.0,
                    "Categoria": "",
                },
                {
                    "Data": "01/01/2024",
                    "Banco/Origem": "B",
                    "Descrição da Transação": "Earlier",
                    "Valor": 2.0,
                    "Categoria": "",
                },
            ])
        ]
        c = Consolidator(output_dir=output_dir)
        path = c.consolidate(frames)
        df = pd.read_csv(path, encoding="utf-8-sig")
        assert df.iloc[0]["Data"] == "01/01/2024"
        assert df.iloc[1]["Data"] == "15/03/2024"

    def test_custom_filename(self, output_dir):
        frames = [
            make_frame([
                {
                    "Data": "01/01/2024",
                    "Banco/Origem": "B",
                    "Descrição da Transação": "X",
                    "Valor": 1.0,
                    "Categoria": "",
                }
            ])
        ]
        c = Consolidator(output_dir=output_dir, output_filename="custom.csv")
        path = c.consolidate(frames)
        assert path.name == "custom.csv"
