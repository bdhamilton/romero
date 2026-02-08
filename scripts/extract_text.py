#!/usr/bin/env python3
"""
Extract text from all downloaded PDFs.
Performs basic cleaning: normalize whitespace, remove tabs.
Uses pdfplumber for better column handling than PyPDF2.
"""

import os
import re
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
    """
    Extract and clean text from a PDF file using pdfplumber.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Cleaned text string, or None if extraction fails
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
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


def extract_all_pdfs(homilies_dir='data/homilies'):
    """
    Extract text from all PDFs in hierarchical homilies directory.
    Text files are saved alongside PDFs: {language}.pdf → {language}.txt

    Args:
        homilies_dir: Base directory containing homilies/{year}/{month}/{day}/{language}.pdf
    """
    # Find all PDF files recursively
    from pathlib import Path
    pdf_paths = sorted(Path(homilies_dir).rglob('*.pdf'))

    total = len(pdf_paths)
    extracted = 0
    skipped = 0
    errors = 0

    print(f"Found {total} PDF files to process")
    print(f"Text files will be saved alongside PDFs")
    print()

    for i, pdf_path in enumerate(pdf_paths, 1):
        # Generate text filename alongside PDF
        # From: homilies/1977/03/14/spanish.pdf
        # To:   homilies/1977/03/14/spanish.txt
        text_path = pdf_path.with_suffix('.txt')

        parts = pdf_path.parts
        year, month, day = parts[-4], parts[-3], parts[-2]

        # Skip if already extracted
        if text_path.exists():
            print(f"[{i}/{total}] Skip (exists): {text_path.name} ({year}-{month}-{day})")
            skipped += 1
            continue

        # Extract text
        print(f"[{i}/{total}] Extracting: {pdf_path.name} ({year}-{month}-{day})")
        text = extract_text_from_pdf(str(pdf_path))

        if text is None:
            errors += 1
            continue

        # Save to text file
        try:
            with open(str(text_path), 'w', encoding='utf-8') as f:
                f.write(text)

            # Show sample (first 100 chars)
            sample = text[:100].replace('\n', ' ')
            print(f"  ✓ Saved ({len(text)} chars): {sample}...")
            extracted += 1

        except Exception as e:
            print(f"  ERROR saving text: {e}")
            errors += 1

    # Summary
    print()
    print("="*60)
    print("Extraction Summary")
    print("="*60)
    print(f"Total PDFs: {total}")
    print(f"Extracted: {extracted}")
    print(f"Skipped (already exist): {skipped}")
    print(f"Errors: {errors}")
    print()
    print(f"Text files saved alongside PDFs in: {homilies_dir}")


if __name__ == "__main__":
    import sys

    print("="*60)
    print("PDF Text Extractor")
    print("="*60)
    print()

    # Check if homilies directory exists
    if not os.path.exists('data/homilies'):
        print("ERROR: data/homilies directory not found")
        print("Download and reorganize PDFs first")
        sys.exit(1)

    # Count PDFs
    from pathlib import Path
    pdf_count = len(list(Path('data/homilies').rglob('*.pdf')))
    if pdf_count == 0:
        print("ERROR: No PDF files found in data/homilies/")
        print("Download and reorganize PDFs first")
        sys.exit(1)

    print(f"Ready to extract text from {pdf_count} PDFs")
    print()

    response = input("Continue? [y/N] ")
    if response.lower() != 'y':
        print("Cancelled")
        sys.exit(0)

    print()
    extract_all_pdfs()
