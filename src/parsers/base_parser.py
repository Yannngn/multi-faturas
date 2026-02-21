"""Abstract base class for all bank PDF parsers."""

import logging
from abc import ABC, abstractmethod

import pandas as pd

logger = logging.getLogger(__name__)

# Required columns in the consolidated output
REQUIRED_COLUMNS = ["Data", "Banco/Origem", "Descrição da Transação", "Valor", "Categoria"]


class BaseParser(ABC):
    """Abstract strategy for parsing a bank's PDF statement.

    Each concrete parser must implement :meth:`parse` and declare the
    bank name it handles via :attr:`bank_name`.
    """

    #: Human-readable bank / origin label used in the CSV output.
    bank_name: str = ""

    def __init__(self, source_path: str) -> None:
        """Initialise the parser with the path to a PDF file.

        Args:
            source_path: Absolute or relative path to the PDF file.
        """
        self.source_path = source_path

    @abstractmethod
    def parse(self) -> pd.DataFrame:
        """Extract transactions from the PDF and return a DataFrame.

        Returns:
            A :class:`pandas.DataFrame` with exactly the columns defined in
            :data:`REQUIRED_COLUMNS`.  *Categoria* may be an empty string.

        Raises:
            ValueError: If the PDF layout is unrecognised.
            FileNotFoundError: If *source_path* does not exist.
        """

    def _build_empty_dataframe(self) -> pd.DataFrame:
        """Return an empty DataFrame with the required schema."""
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    def _validate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure *df* contains all required columns.

        Missing columns are added with ``None`` values so that downstream
        consolidation never fails due to a schema mismatch.

        Args:
            df: DataFrame to validate.

        Returns:
            The validated (and possibly patched) DataFrame.
        """
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                logger.warning(
                    "Parser '%s' is missing column '%s'. Filling with None.",
                    self.bank_name,
                    col,
                )
                df[col] = None
        return df[REQUIRED_COLUMNS]
