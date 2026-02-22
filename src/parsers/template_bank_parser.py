"""Template / example concrete parser.

Copy this file and rename it to match the target bank (e.g.
``nubank_parser.py``).  Then implement :meth:`parse` to extract
transactions from the bank's specific PDF layout.
"""

import logging
import os
import re
from datetime import datetime

import pandas as pd
import pdfplumber

from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class TemplateBankParser(BaseParser):
    """Example parser - replace with real extraction logic for your bank."""

    bank_name = "Template Bank"

    def parse(self) -> pd.DataFrame:
        """Extract transactions from the PDF.

        This skeleton reads every page, looks for lines that contain a
        date pattern (DD/MM/YYYY), a description, and a monetary value.
        Adapt the regular-expression / table-extraction logic to match
        the actual PDF layout of the target bank.

        Returns:
            DataFrame with columns:
            Data, Banco/Origem, Descrição da Transação, Valor, Categoria.

        Raises:
            FileNotFoundError: If the PDF file does not exist.
            ValueError: If no transactions could be extracted.
        """
        rows: list[dict] = []
        card_last_digits: str | None = None

        logger.info("Parsing '%s' with %s.", self.source_path, self.__class__.__name__)

        with self._open_pdf() as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                if card_last_digits is None:
                    text = page.extract_text() or ""
                    card_last_digits = self._extract_card_last_digits(text)

                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        parsed = self._parse_row(row)
                        if parsed:
                            rows.append(parsed)

                if not tables:
                    logger.debug(
                        "Page %d of '%s': no tables found, skipping.",
                        page_num,
                        self.source_path,
                    )

        if not rows:
            raise ValueError(
                f"No transactions found in '{self.source_path}'. The PDF layout may not match this parser."
            )

        df = pd.DataFrame(rows)
        df = self._validate_dataframe(df)
        if card_last_digits:
            df.attrs["card_last_digits"] = card_last_digits
        return df

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_row(self, row: list) -> dict | None:
        """Attempt to extract a transaction from a single table row.

        Override this method with bank-specific logic.

        Args:
            row: List of cell strings from ``pdfplumber`` table extraction.

        Returns:
            A dict with keys matching :data:`~base_parser.REQUIRED_COLUMNS`,
            or ``None`` if the row does not represent a transaction.
        """
        if not row or len(row) < 3:
            return None

        raw_date, raw_description, raw_value = row[0], row[1], row[2]

        # Validate date format
        try:
            date_str = datetime.strptime(str(raw_date).strip(), "%d/%m/%Y").strftime(
                "%d/%m/%Y"
            )
        except (ValueError, TypeError):
            return None

        # Convert Brazilian decimal format to float (1.234,56 -> 1234.56)
        try:
            value = self._parse_brl_value(str(raw_value))
        except ValueError:
            logger.debug("Could not parse value '%s', skipping row.", raw_value)
            return None

        description = str(raw_description).strip() if raw_description else ""

        return {
            "Data": date_str,
            "Banco/Origem": self.bank_name,
            "Descrição da Transação": description,
            "Valor": value,
            "Categoria": "",
        }

    def _open_pdf(self) -> pdfplumber.PDF:
        passwords = [None, *self._cpf_password_candidates()]
        last_exc: Exception | None = None

        for password in passwords:
            try:
                return pdfplumber.open(self.source_path, password=password)
            except FileNotFoundError:
                raise
            except Exception as exc:
                last_exc = exc

        if last_exc is not None:
            raise last_exc

        # This point is unreachable since passwords always contains at least None,
        # but satisfies the type checker that we always return or raise.
        raise RuntimeError("No password attempts were made")  # pragma: no cover

    @staticmethod
    def _cpf_password_candidates() -> list[str]:
        raw_cpf = os.getenv("CPF", "").strip()
        digits = re.sub(r"\D", "", raw_cpf)
        if not digits:
            return []

        candidates: list[str] = []
        for length in (6, 5):
            if len(digits) >= length:
                candidates.append(digits[:length])

        if digits not in candidates:
            candidates.append(digits)

        # Preserve order while removing duplicates.
        unique: list[str] = []
        for candidate in candidates:
            if candidate not in unique:
                unique.append(candidate)
        return unique

    @staticmethod
    def _parse_brl_value(raw: str) -> float:
        """Convert a Brazilian-formatted number string to a Python float.

        Examples::

            "1.234,56"  -> 1234.56
            "-200,00"   -> -200.0
            "R$ 50,00"  -> 50.0

        Args:
            raw: Raw string as it appears in the PDF.

        Returns:
            Parsed float value.

        Raises:
            ValueError: If the string cannot be converted.
        """
        # Strip currency symbols, non-breaking spaces, and whitespace
        cleaned = raw.replace("R$", "").replace("\xa0", "").strip()
        # Remove any remaining alphabetic characters (e.g. lone "R")
        cleaned = re.sub(r"[A-Za-z\s]", "", cleaned)
        # Convert from BRL format (1.234,56) to float format (1234.56)
        cleaned = cleaned.replace(".", "").replace(",", ".")
        return float(cleaned)

    @staticmethod
    def _extract_card_last_digits(text: str) -> str | None:
        patterns = [
            r"(?:\*{2,}|x{2,}|X{2,})\s*(\d{4})",
            r"(?:final|ultimos|\u00faltimos)\s*(\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None
