"""PDF extraction manager.

Responsible for discovering PDF files in the input directory and
delegating parsing to the appropriate concrete :class:`BaseParser`.
"""

import logging
import os
from pathlib import Path
from typing import Type

import pandas as pd

from .parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class Extractor:
    """Manages the reading of PDF files from an input directory.

    The extractor applies a *Strategy* pattern: a mapping of
    bank-name strings to :class:`BaseParser` subclasses is provided at
    construction time.  Files whose names contain a known bank key are
    dispatched to the matching parser; unrecognised files are skipped
    with a warning.

    Args:
        input_dir: Path to the directory containing PDF statements.
        parser_registry: Mapping of lower-case bank identifiers to
            :class:`BaseParser` subclasses.

    Example::

        from src.parsers.template_bank_parser import TemplateBankParser

        extractor = Extractor(
            input_dir="data/input",
            parser_registry={"templatebank": TemplateBankParser},
        )
        frames = extractor.extract_all()
    """

    def __init__(
        self,
        input_dir: str | os.PathLike,
        parser_registry: dict[str, Type[BaseParser]],
    ) -> None:
        self.input_dir = Path(input_dir)
        self.parser_registry = {k.lower(): v for k, v in parser_registry.items()}

    def extract_all(self) -> list[pd.DataFrame]:
        """Iterate over PDFs in *input_dir* and parse each one.

        Returns:
            List of DataFrames, one per successfully parsed file.
            Files that fail are logged and skipped.
        """
        pdf_files = sorted(self.input_dir.glob("*.pdf"))

        if not pdf_files:
            logger.warning("No PDF files found in '%s'.", self.input_dir)
            return []

        frames: list[pd.DataFrame] = []

        for pdf_path in pdf_files:
            parser_cls = self._resolve_parser(pdf_path)
            if parser_cls is None:
                logger.warning(
                    "No parser registered for '%s'. Skipping.", pdf_path.name
                )
                continue

            try:
                parser = parser_cls(str(pdf_path))
                df = parser.parse()
                frames.append(df)
                logger.info("Successfully parsed '%s'.", pdf_path.name)
            except FileNotFoundError:
                logger.error("File not found: '%s'.", pdf_path)
            except PermissionError:
                logger.error(
                    "Cannot open '%s': file may be password-protected.", pdf_path.name
                )
            except ValueError as exc:
                logger.error("Failed to parse '%s': %s", pdf_path.name, exc)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Unexpected error while parsing '%s': %s", pdf_path.name, exc
                )

        return frames

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_parser(self, pdf_path: Path) -> Type[BaseParser] | None:
        """Return the parser class whose key appears in the file name.

        Matching is case-insensitive and uses the file *stem* (name
        without extension).

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Matching :class:`BaseParser` subclass, or ``None``.
        """
        stem_lower = pdf_path.stem.lower()
        for key, parser_cls in self.parser_registry.items():
            if key in stem_lower:
                return parser_cls
        return None
