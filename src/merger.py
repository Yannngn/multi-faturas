"""Consolidates multiple transaction DataFrames and exports a CSV file."""

import logging
import os
from pathlib import Path

import pandas as pd

from .parsers.base_parser import REQUIRED_COLUMNS

logger = logging.getLogger(__name__)


class DataMerger:
    """Merges parsed DataFrames and writes a single consolidated CSV.

    Args:
        output_dir: Directory where consolidated and per-bank outputs are saved.

    Example::

        merger = DataMerger(output_dir="data/output")
        merger.consolidate(frames)
    """

    def __init__(
        self,
        output_dir: str | os.PathLike,
    ) -> None:
        self.output_dir = Path(output_dir)

    def consolidate(self, frames: list[pd.DataFrame]) -> Path | None:
        """Merge *frames*, sort by date, and write to CSVs.

        Args:
            frames: List of DataFrames returned by :class:`~extractor.Extractor`.

        Returns:
            :class:`pathlib.Path` to the output CSV, or ``None`` if there
            was nothing to consolidate.
        """
        if not frames:
            logger.warning("No data to consolidate.")
            return None

        combined = pd.concat(frames, ignore_index=True)

        # Ensure all required columns are present
        for col in REQUIRED_COLUMNS:
            if col not in combined.columns:
                combined[col] = None

        combined = combined[REQUIRED_COLUMNS]

        # Sort by date ascending (parse DD/MM/YYYY for sorting only)
        try:
            combined["_sort_date"] = pd.to_datetime(
                combined["Data"], format="%d/%m/%Y", errors="coerce"
            )
            combined.sort_values("_sort_date", inplace=True, ignore_index=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not sort by date: %s", exc)
        finally:
            if "_sort_date" in combined.columns:
                combined.drop(columns=["_sort_date"], inplace=True)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        period_label = self._format_period_from_series(combined["Data"])
        output_path = self.output_dir / f"faturas_consolidadas_{period_label}.csv"

        combined.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info(
            "Consolidated %d transaction(s) into '%s'.",
            len(combined),
            output_path,
        )

        self._write_per_bank_outputs(frames)

        return output_path

    def _write_per_bank_outputs(self, frames: list[pd.DataFrame]) -> None:
        counters: dict[tuple[str, str], int] = {}

        for frame in frames:
            bank_id = str(frame.attrs.get("bank_id", "unknown")).lower()
            bank_dir = self.output_dir / bank_id
            bank_dir.mkdir(parents=True, exist_ok=True)

            period_label = self._format_period_from_series(frame["Data"])
            card_last = frame.attrs.get("card_last_digits")

            if not card_last:
                key = (bank_id, period_label)
                counters[key] = counters.get(key, 0) + 1
                card_last = str(counters[key])

            filename = f"fatura_{bank_id}_{card_last}_{period_label}.csv"
            output_path = bank_dir / filename
            frame.to_csv(output_path, index=False, encoding="utf-8-sig")

    @staticmethod
    def _format_period_from_series(series: pd.Series) -> str:
        dates = pd.to_datetime(series, format="%d/%m/%Y", errors="coerce")
        dates = dates.dropna()
        if dates.empty:
            return "periodo-indefinido"

        start = dates.min()
        end = dates.max()
        return DataMerger._format_period(start, end)

    @staticmethod
    def _format_period(start: pd.Timestamp, end: pd.Timestamp) -> str:
        start_label = DataMerger._format_month_year(start)
        end_label = DataMerger._format_month_year(end)
        if start_label == end_label:
            return start_label
        return f"{start_label}_{end_label}"

    @staticmethod
    def _format_month_year(date: pd.Timestamp) -> str:
        months = {
            1: "jan",
            2: "fev",
            3: "mar",
            4: "abr",
            5: "mai",
            6: "jun",
            7: "jul",
            8: "ago",
            9: "set",
            10: "out",
            11: "nov",
            12: "dez",
        }
        return f"{months[date.month]}-{date.year}"
