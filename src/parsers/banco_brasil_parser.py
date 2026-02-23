"""Banco do Brasil PDF statement parser.

Extracts transaction details from Banco do Brasil faturas PDFs into structured CSV format.
Designed with exploratory/iterative refinement in mind - includes detailed logging to
understand PDF structure and identify parsing edge cases.

Note: BB faturas have text-based layouts (not tables), so extraction uses regex pattern
matching on raw text rather than pdfplumber table extraction.
"""

import logging
import os
import re
from datetime import datetime

import pandas as pd
import pdfplumber

from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class BancoBrasilParser(BaseParser):
    """Parser for Banco do Brasil fatura PDFs."""

    bank_name = "Banco do Brasil"

    def parse(self) -> pd.DataFrame:
        """Extract transactions from Banco do Brasil PDF.

        This parser extracts transaction data from text-based layouts (not tables).
        It identifies the statement date from the PDF, then extracts individual
        transaction lines using regex pattern matching.

        Returns:
            DataFrame with columns:
            Data, Banco/Origem, Descrição da Transação, Valor, Categoria.

        Raises:
            FileNotFoundError: If the PDF file does not exist.
            ValueError: If no transactions could be extracted.
        """
        rows: list[dict] = []
        card_last_digits: str | None = None
        total_pages = 0
        all_text = ""

        logger.info("Parsing '%s' with %s.", self.source_path, self.__class__.__name__)

        with self._open_pdf() as pdf:
            total_pages = len(pdf.pages)
            logger.debug("PDF has %d pages", total_pages)

            # Extract all text to find transactions
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract card last digits from first page text
                if card_last_digits is None:
                    text = page.extract_text() or ""
                    card_last_digits = self._extract_card_last_digits(text)

                all_text += "\n" + (page.extract_text() or "")

        # Extract the statement month/year from vencimento
        month_year = self._extract_month_year(all_text)
        logger.debug("Extracted month/year from vencimento: %s", month_year)

        # Parse transaction lines from the text
        rows = self._parse_transaction_lines(all_text, month_year)
        logger.info(
            "Extraction summary: %d pages, %d transactions extracted",
            total_pages,
            len(rows),
        )

        if not rows:
            raise ValueError(
                f"No transactions found in '{self.source_path}'. Examined {total_pages} pages. The PDF layout may not match this parser."
            )

        df = pd.DataFrame(rows)
        df = self._validate_dataframe(df)
        if card_last_digits:
            df.attrs["card_last_digits"] = card_last_digits
        return df

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_month_year(self, text: str) -> tuple[int, int]:
        """Extract month and year from vencimento (due date) in the PDF text.

        Looks for pattern like "Vencimento" followed by a date like "28/10/2025".
        Handles both same-line and multi-line formats with flexible whitespace.

        Args:
            text: Full extracted text from the PDF.

        Returns:
            Tuple of (month, year) e.g. (10, 2025).

        Raises:
            ValueError: If vencimento date cannot be found.
        """
        # Try multiple patterns to find the vencimento date
        # Pattern 1: "Vencimento" followed by date (allows for newlines/spaces)
        pattern1 = r"Vencimento[\s\S]{0,200}?(\d{2})/(\d{2})/(\d{4})"

        # Pattern 2: Direct date pattern (as fallback)
        pattern2 = r"(\d{2})/(\d{2})/(\d{4})"

        match = re.search(pattern1, text)
        if match:
            day, month, year = match.groups()
            logger.debug(
                "Found vencimento (pattern 1): %s/%s/%s → using month %s, year %s",
                day,
                month,
                year,
                month,
                year,
            )
            return int(month), int(year)

        # Fallback: try to find any date (typically the first one is vencimento)
        match = re.search(pattern2, text)
        if match:
            day, month, year = match.groups()
            # Make sure it's a valid month
            if 1 <= int(month) <= 12:
                logger.debug(
                    "Found vencimento (pattern 2, fallback): %s/%s/%s → using month %s, year %s",
                    day,
                    month,
                    year,
                    month,
                    year,
                )
                return int(month), int(year)

        raise ValueError(
            "Could not extract vencimento date from PDF. Cannot determine transaction month/year."
        )

    def _parse_transaction_lines(
        self, text: str, month_year: tuple[int, int]
    ) -> list[dict]:
        """Parse transaction lines from extracted text.

        Looks for lines matching pattern: DD/MM <description> <country> R$ <amount>

        Args:
            text: Full extracted text from the PDF.
            month_year: Tuple of (month, year) to complete partial dates.

        Returns:
            List of transaction dicts.
        """
        rows: list[dict] = []
        month, year = month_year

        # Pattern to match transaction lines:
        # Starts with DD/MM, then has description, country code, and R$ amount
        # Example: "01/10 MP*CARVALHOLANCE JOAO PESSOA BR R$ 8,00"
        # More flexible pattern that captures the key parts
        transaction_pattern = (
            r"^(\d{2})/(\d{2})\s+(.+?)\s+(BR|US|[A-Z]{2})\s+R\$\s+([\d.,]+)$"
        )

        for line in text.split("\n"):
            line = line.strip()

            # Skip empty lines, headers, and non-transaction lines
            if not line or line.startswith("Data Descrição") or "Valor" in line:
                continue

            match = re.match(transaction_pattern, line)
            if match:
                day_str, month_str, description, country, value_str = match.groups()
                day = int(day_str)
                tx_month = int(month_str)

                # Validate month (should match the statement month or be close)
                if abs(tx_month - month) > 1 and not (
                    month == 1 and tx_month == 12
                ):  # Allow rollover
                    logger.debug(
                        "Skipping line with mismatched month %d (expected ~%d): %s",
                        tx_month,
                        month,
                        line,
                    )
                    continue

                try:
                    date_str = f"{day:02d}/{tx_month:02d}/{year}"
                    # Validate date format
                    datetime.strptime(date_str, "%d/%m/%Y")

                    # Parse amount
                    value = self._parse_brl_value(f"R$ {value_str}")

                    parsed = {
                        "Data": date_str,
                        "Banco/Origem": self.bank_name,
                        "Descrição da Transação": description.strip(),
                        "Valor": value,
                        "Categoria": "",
                    }
                    rows.append(parsed)
                    logger.debug(
                        "Parsed transaction: %s - %s (R$ %.2f)",
                        date_str,
                        description.strip(),
                        value,
                    )

                except (ValueError, TypeError) as e:
                    logger.debug(
                        "Failed to parse transaction line: %s (error: %s)",
                        line,
                        e,
                    )
                    continue

        return rows

    def _parse_row(self, row: list) -> dict | None:
        """Attempt to extract a transaction from a single table row.

        Note: BB PDFs use text layout, not tables. This method is kept for
        compatibility but typically won't be used.

        Args:
            row: List of cell strings from ``pdfplumber`` table extraction.

        Returns:
            A dict with keys matching :data:`~base_parser.REQUIRED_COLUMNS`,
            or ``None`` if the row does not represent a transaction.
        """
        if not row or len(row) < 3:
            return None

        raw_date = row[0]
        raw_description = row[1] if len(row) > 1 else ""
        raw_value = row[2] if len(row) > 2 else ""

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

        # Skip empty descriptions
        if not description:
            return None

        return {
            "Data": date_str,
            "Banco/Origem": self.bank_name,
            "Descrição da Transação": description,
            "Valor": value,
            "Categoria": "",
        }

    def _open_pdf(self) -> pdfplumber.PDF:
        """Open PDF with password attempts."""
        passwords = [None, *self._cpf_password_candidates()]
        last_exc: Exception | None = None

        for password in passwords:
            try:
                logger.debug(
                    "Attempting to open PDF with password: %s",
                    "None" if password is None else f"***{password[-2:]}",
                )
                return pdfplumber.open(self.source_path, password=password)
            except FileNotFoundError:
                raise
            except Exception as exc:
                logger.debug("Failed with password attempt (will retry): %s", exc)
                last_exc = exc

        if last_exc is not None:
            raise last_exc

        # This point is unreachable since passwords always contains at least None,
        # but satisfies the type checker that we always return or raise.
        raise RuntimeError("No password attempts were made")  # pragma: no cover

    @staticmethod
    def _cpf_password_candidates() -> list[str]:
        """Generate CPF-based password candidates from .env."""
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
        """Extract last 4 digits of card number from text."""
        patterns = [
            r"(?:\*{2,}|x{2,}|X{2,})\s*(\d{4})",
            r"(?:final|ultimos|\u00faltimos)\s*(\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None
