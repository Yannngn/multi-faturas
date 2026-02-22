"""Unit tests for the Merger."""

import pandas as pd
import pytest

from src.merger import DataMerger
from src.parsers.base_parser import REQUIRED_COLUMNS


def make_frame(rows: list[dict], bank_id: str = "bank") -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=REQUIRED_COLUMNS)
    df.attrs["bank_id"] = bank_id
    return df


@pytest.fixture
def output_dir(tmp_path):
    return tmp_path / "output"


class TestDataMergerWithNoInput:
    def test_returns_none_when_no_frames(self, output_dir):
        c = DataMerger(output_dir=output_dir)
        assert c.consolidate([]) is None


class TestDataMergerWithData:
    def test_creates_csv(self, output_dir):
        frames = [
            make_frame(
                [
                    {
                        "Data": "10/01/2024",
                        "Banco/Origem": "TestBank",
                        "Descrição da Transação": "Café",
                        "Valor": 5.50,
                        "Categoria": "",
                    }
                ],
                bank_id="bb",
            )
        ]
        c = DataMerger(output_dir=output_dir)
        path = c.consolidate(frames)
        assert path is not None
        assert path.exists()
        assert path.name == "faturas_consolidadas_jan-2024.csv"
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
        frames = [make_frame([row], bank_id="a"), make_frame([row], bank_id="a")]
        c = DataMerger(output_dir=output_dir)
        path = c.consolidate(frames)
        df = pd.read_csv(path, encoding="utf-8-sig")  # ty:ignore[no-matching-overload]
        assert len(df) == 2

    def test_sorted_by_date(self, output_dir):
        frames = [
            make_frame(
                [
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
                ]
            )
        ]
        c = DataMerger(output_dir=output_dir)
        path = c.consolidate(frames)
        df = pd.read_csv(path, encoding="utf-8-sig")  # ty:ignore[no-matching-overload]
        assert df.iloc[0]["Data"] == "01/01/2024"
        assert df.iloc[1]["Data"] == "15/03/2024"

    def test_per_bank_outputs(self, output_dir):
        frames = [
            make_frame(
                [
                    {
                        "Data": "01/02/2024",
                        "Banco/Origem": "BB",
                        "Descrição da Transação": "X",
                        "Valor": 1.0,
                        "Categoria": "",
                    }
                ],
                bank_id="bb",
            )
        ]
        c = DataMerger(output_dir=output_dir)
        c.consolidate(frames)
        bank_dir = output_dir / "bb"
        outputs = list(bank_dir.glob("*.csv"))
        assert len(outputs) == 1
