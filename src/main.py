"""CLI entry point for multi-faturas.

Usage::

    python -m src.main --root data
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from .extractor import Extractor
from .merger import DataMerger
from .parsers.base_parser import BaseParser
from .parsers.template_bank_parser import TemplateBankParser

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parser registry  –  add new bank parsers here
# ---------------------------------------------------------------------------

PARSER_REGISTRY = {
    "templatebank": TemplateBankParser,
    # "nubank": NubankParser,
    # "itau": ItauParser,
    # "bb": BancoDoBrasilParser,
}

BANK_ALIASES = {
    "templatebank": "templatebank",
    "bb": "bb",
    "bancobrasil": "bb",
    "nubank": "nubank",
    "itau": "itau",
    "bradesco": "bradesco",
    "bancobradesco": "bradesco",
    "inter": "inter",
    "c6": "c6",
    "c6bank": "c6",
    "santander": "santander",
    "caixa": "caixa",
    "caixa_economica": "caixa",
    "sicoob": "sicoob",
    "sicredi": "sicredi",
}

load_dotenv()  # Load environment variables from .env file if file is present

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    """Return the configured argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="multi-faturas",
        description="Extract and consolidate bank statements from PDFs into a CSV.",
    )
    parser.add_argument(
        "--root",
        "-r",
        type=Path,
        default=Path(os.getenv("ROOT_DATA_DIR", ".")),
        help="Root directory with bank folders (default: ROOT_DATA_DIR or .).",
    )
    return parser


def _make_fallback_parser(canonical_key: str) -> type[BaseParser]:
    class FallbackParser(BaseParser):
        bank_name = f"Unknown ({canonical_key})"

        def parse(self) -> pd.DataFrame:
            raise ValueError(
                f"No parser registered for bank '{canonical_key}'. Register a parser in PARSER_REGISTRY."
            )

    return FallbackParser


def validate_parsers_on_startup(
    parser_registry: dict[str, type[BaseParser]],
    bank_aliases: dict[str, str],
) -> dict[str, type[BaseParser]]:
    missing = sorted(
        {
            canonical
            for canonical in bank_aliases.values()
            if canonical not in parser_registry
        }
    )
    if not missing:
        return parser_registry

    for canonical in missing:
        parser_registry[canonical] = _make_fallback_parser(canonical)

    return parser_registry


def main(argv: list[str] | None = None) -> int:
    """Run the full ETL pipeline and return an exit code.

    Args:
        argv: Optional argument list (uses ``sys.argv`` when ``None``).

    Returns:
        ``0`` on success, ``1`` on failure.
    """
    load_dotenv()
    args = build_arg_parser().parse_args(argv)

    logger.info("Starting multi-faturas pipeline.")
    logger.info("Root directory  : %s", args.root)

    input_root = args.root
    output_root = args.root / "output"

    # --- Extract ---
    parser_registry = validate_parsers_on_startup(PARSER_REGISTRY, BANK_ALIASES)
    extractor = Extractor(
        root_dir=input_root,
        parser_registry=parser_registry,
        bank_aliases=BANK_ALIASES,
    )
    frames = extractor.extract_all()

    # --- Consolidate & Export ---
    merger = DataMerger(
        output_dir=output_root,
    )
    output_path = merger.consolidate(frames)

    if output_path is None:
        logger.warning("Pipeline finished with no output produced.")
        return 1

    logger.info("Pipeline finished successfully. Output: %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
