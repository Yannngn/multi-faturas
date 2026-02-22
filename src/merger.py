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
        output_dir: Directory where the output CSV will be saved.
        output_filename: Name of the CSV file (default:
            ``"faturas_consolidadas.csv"``).

    Example::

        merger = DataMerger(output_dir="data/output")
        merger.consolidate(frames)
    """

    def __init__(
        self,
        output_dir: str | os.PathLike,
        output_filename: str = "faturas_consolidadas.csv",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_filename = output_filename

    def consolidate(self, frames: list[pd.DataFrame]) -> Path | None:
        """Merge *frames*, sort by date, and write to CSV.

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
                combined["Data"], format="%d/%m/%Y", dayfirst=True, errors="coerce"
            )
            combined.sort_values("_sort_date", inplace=True, ignore_index=True)
            combined.drop(columns=["_sort_date"], inplace=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not sort by date: %s", exc)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / self.output_filename

        combined.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info(
            "Consolidated %d transaction(s) into '%s'.",
            len(combined),
            output_path,
        )

        return output_path
