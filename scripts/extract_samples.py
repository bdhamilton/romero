#!/usr/bin/env python3
"""
Extract text from just 4 sample PDFs for testing.
Uses pdfplumber for better column handling.
"""

import re
from pathlib import Path
import pdfplumber


def clean_text(text):
    """
    Clean extracted PDF text.

    - Fix hyphenated words split across lines
    - Add spaces where newlines were removed without spacing
    - Remove headers, footers, and page numbers
    - Replace tabs with spaces
    - Normalize multiple spaces to single space
    - Normalize multiple newlines
    - Strip leading/trailing whitespace
    """
    # First: Fix hyphenated words across line breaks: "herma-\nnos" → "hermanos"
    # MUST be done before adding spaces at newlines!
    text = re.sub(r'-\n', '', text)

    # Second: Add space where newline separates words: "la\nrica" → "la rica"
    # Match non-whitespace, newline, non-whitespace
    text = re.sub(r'([^\s])\n([^\s])', r'\1 \2', text)

    # Remove common headers and footers
    # Spanish running headers: "‡ Ciclo C, 1977 ‡", "‡ Homilías de Monseñor Romero ‡"
    text = re.sub(r'‡\s*Ciclo [ABC],\s*\d{4}\s*‡', '', text)
    text = re.sub(r'‡\s*Homilías de Monseñor Romero\s*‡', '', text)

    # English running headers: "St Oscar Romero, ...", "Read or listen to..."
    text = re.sub(r'St Oscar Romero,.*?(?:\d{1,2} [A-Z][a-z]+ \d{4}|\d+ [A-Z][a-z]+ \d{4})', '', text)
    text = re.sub(r'Read or listen to the homilies of St Oscar Romero at romerotrust\.org\.uk', '', text)

    # Remove standalone page numbers (digits on their own line or at end of line)
    text = re.sub(r'\n\d+\s*\n', '\n', text)  # Page number on its own line
    text = re.sub(r'\s+\d+\s*$', '', text, flags=re.MULTILINE)  # Page number at end of line

    # Replace tabs with spaces
    text = text.replace('\t', ' ')

    # Normalize whitespace
    text = re.sub(r' +', ' ', text)  # Multiple spaces → single space
    text = re.sub(r'\n ', '\n', text)  # Remove spaces after newlines
    text = re.sub(r' \n', '\n', text)  # Remove spaces before newlines
    text = re.sub(r'\n\n\n+', '\n\n', text)  # Multiple newlines → double newline

    return text.strip()


def extract_text_from_pdf(pdf_path):
    """Extract and clean text from a PDF file using pdfplumber."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            # Extract text from all pages
            all_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

            # Join pages with double newline
            full_text = "\n\n".join(all_text)

            # Clean the text
            cleaned = clean_text(full_text)

            return cleaned

    except Exception as e:
        print(f"  ERROR extracting text: {e}")
        return None


# Extract 4 sample PDFs
samples = [
    'data/homilies/1977/03/14/spanish.pdf',
    'data/homilies/1977/03/14/english.pdf',
    'data/homilies/1977/04/17/spanish.pdf',
    'data/homilies/1977/04/17/english.pdf',
]

for pdf_path in samples:
    pdf_path = Path(pdf_path)
    text_path = pdf_path.with_suffix('.txt')

    print(f"Extracting: {pdf_path}")
    text = extract_text_from_pdf(str(pdf_path))

    if text:
        with open(str(text_path), 'w', encoding='utf-8') as f:
            f.write(text)

        sample = text[:100].replace('\n', ' ')
        print(f"  ✓ Saved ({len(text)} chars): {sample}...")
    else:
        print(f"  ❌ Failed")

print("\nDone!")
