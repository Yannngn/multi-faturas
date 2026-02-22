"""CLI entry point for multi-faturas.

Usage::

    python -m src.main --input data/input --output data/output

    # Specify a custom output file name:
    python -m src.main --input data/input --output data/output \\
        --filename meu_relatorio.csv
"""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from .extractor import Extractor
from .merger import DataMerger
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
}


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
        "--input",
        "-i",
        type=Path,
        default=Path("data/input"),
        help="Directory containing PDF statements (default: data/input).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/output"),
        help="Directory where the consolidated CSV will be saved (default: data/output).",
    )
    parser.add_argument(
        "--filename",
        "-f",
        type=str,
        default="faturas_consolidadas.csv",
        help="Output CSV file name (default: faturas_consolidadas.csv).",
    )
    return parser


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
    logger.info("Input directory : %s", args.input)
    logger.info("Output directory: %s", args.output)

    # --- Extract ---
    extractor = Extractor(
        input_dir=args.input,
        parser_registry=PARSER_REGISTRY,
    )
    frames = extractor.extract_all()

    # --- Consolidate & Export ---
    merger = DataMerger(
        output_dir=args.output,
        output_filename=args.filename,
    )
    output_path = merger.consolidate(frames)

    if output_path is None:
        logger.warning("Pipeline finished with no output produced.")
        return 1

    logger.info("Pipeline finished successfully. Output: %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
