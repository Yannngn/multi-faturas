"""PDF extraction manager.

Responsible for discovering PDF files in bank folders under a root
directory and delegating parsing to the appropriate concrete
:class:`BaseParser`.
"""

import logging
import os
from pathlib import Path
from typing import Type

import pandas as pd

from .parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class Extractor:
    """Manages the reading of PDF files from a root data directory.

    The extractor applies a *Strategy* pattern: a mapping of
    canonical bank identifiers to :class:`BaseParser` subclasses is
    provided at construction time. Bank folders are matched using
    configurable aliases and normalized into canonical ids.

    Args:
        root_dir: Root directory containing bank subfolders with PDFs.
        parser_registry: Mapping of canonical bank identifiers to
            :class:`BaseParser` subclasses.
        bank_aliases: Mapping of alias strings to canonical identifiers.

    Example::

        from src.parsers.template_bank_parser import TemplateBankParser

        extractor = Extractor(
            root_dir="data",
            parser_registry={"templatebank": TemplateBankParser},
            bank_aliases={"templatebank": "templatebank"},
        )
        frames = extractor.extract_all()
    """

    def __init__(
        self,
        root_dir: str | os.PathLike,
        parser_registry: dict[str, Type[BaseParser]],
        bank_aliases: dict[str, str] | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.parser_registry = {k.lower(): v for k, v in parser_registry.items()}
        self.bank_aliases = self._build_alias_map(bank_aliases)

    def extract_all(self) -> list[pd.DataFrame]:
        """Iterate over bank folders in *root_dir* and parse PDFs.

        Returns:
            List of DataFrames, one per successfully parsed file.
            Files that fail are logged and skipped.
        """
        frames: list[pd.DataFrame] = []

        bank_dirs = sorted(
            path
            for path in self.root_dir.iterdir()
            if path.is_dir() and path.name != "output"
        )
        if not bank_dirs:
            logger.warning("No bank folders found in '%s'.", self.root_dir)
            return []

        for bank_dir in bank_dirs:
            bank_key = self._resolve_bank_id(bank_dir.name)
            if bank_key is None:
                logger.warning(
                    "No parser registered for bank folder '%s'. Skipping.",
                    bank_dir.name,
                )
                continue

            parser_cls = self.parser_registry[bank_key]

            pdf_files = sorted(bank_dir.glob("*.pdf"))
            if not pdf_files:
                logger.warning("No PDF files found in '%s'.", bank_dir)
                continue

            for pdf_path in pdf_files:
                try:
                    parser = parser_cls(str(pdf_path))
                    df = parser.parse()
                    df.attrs["bank_id"] = bank_key
                    df.attrs["bank_name"] = parser.bank_name
                    df.attrs["source_path"] = str(pdf_path)
                    frames.append(df)
                    logger.info("Successfully parsed '%s'.", pdf_path.name)
                except FileNotFoundError:
                    logger.error("File not found: '%s'.", pdf_path)
                except PermissionError:
                    logger.error("Cannot open '%s': permission denied.", pdf_path.name)
                except ValueError as exc:
                    logger.error("Failed to parse '%s': %s", pdf_path.name, exc)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Unexpected error while parsing '%s': %s", pdf_path.name, exc
                    )

        return frames

    def _resolve_bank_id(self, folder_name: str) -> str | None:
        normalized = self._normalize_bank_key(folder_name)
        return self.bank_aliases.get(normalized)

    def _build_alias_map(self, bank_aliases: dict[str, str] | None) -> dict[str, str]:
        aliases = bank_aliases or {}
        alias_map: dict[str, str] = {}

        for canonical in self.parser_registry:
            alias_map[self._normalize_bank_key(canonical)] = canonical

        for alias, canonical in aliases.items():
            canonical_key = canonical.lower()
            if canonical_key in self.parser_registry:
                alias_map[self._normalize_bank_key(alias)] = canonical_key

        return alias_map

    @staticmethod
    def _normalize_bank_key(name: str) -> str:
        normalized = name.lower()
        for token in (" do ", " da ", " de ", " dos ", " das "):
            normalized = normalized.replace(token, " ")
        parts: list[str] = []
        current = []
        for ch in normalized:
            if ch.isalnum():
                current.append(ch)
            else:
                if current:
                    parts.append("".join(current))
                    current = []
        if current:
            parts.append("".join(current))
        return "".join(parts)
