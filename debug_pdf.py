"""Debug script to inspect Banco do Brasil PDF structure."""

import os
import sys

import pdfplumber
from dotenv import load_dotenv

load_dotenv()

PDF_PATH = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "/mnt/g/My Drive/[04] DOCUMENTS/Faturas/BB/OUROCARD INTERN. VISA-UNIV. (1).pdf"
)

NUMBER_OF_CHARS_FOR_PASSWORD = 5

print(f"\n{'=' * 80}")
print(f"Inspecting: {PDF_PATH}")
print(f"{'=' * 80}\n")

# Try without password first
try:
    pdf_obj = pdfplumber.open(PDF_PATH)
    print("✓ Successfully opened without password\n")
except Exception as e:
    print(f"✗ Failed to open without password: {e}")
    print("Trying password candidates...\n")
    pdf_obj = pdfplumber.open(
        PDF_PATH, password=os.getenv("CPF", "")[:NUMBER_OF_CHARS_FOR_PASSWORD]
    )

with pdf_obj as pdf:
    print(f"Total pages: {len(pdf.pages)}\n")

    for page_num, page in enumerate(pdf.pages, start=1):
        print(f"\n{'=' * 80}")
        print(f"PAGE {page_num}")
        print(f"{'=' * 80}")

        # Check for tables
        tables = page.extract_tables()
        print(f"Tables found: {len(tables)}")
        if tables:
            for idx, table in enumerate(tables):
                print(f"\nTable {idx}: {len(table)} rows")
                for row_idx, row in enumerate(table[:5]):
                    print(f"  Row {row_idx}: {row}")

        # Extract raw text
        text = page.extract_text()
        print("\nRaw text preview (first 1000 chars):")
        print(text[:1000] if text else "(no text)")

        # Check for lines
        lines = page.lines
        print(f"\nLines found: {len(lines)}")

        # Check for rects
        rects = page.rects
        print(f"Rectangles found: {len(rects)}")
