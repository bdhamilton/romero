#!/usr/bin/env python3
"""
Reorganize PDFs into hierarchical directory structure.
From: data/pdfs/YYYY-MM-DD_{language}_{index}.pdf
To:   homilies/{year}/{month}/{day}/{spanish|english}.pdf
"""

import os
import shutil
from pathlib import Path


def reorganize_pdfs(source_dir='data/pdfs', target_base='homilies'):
    """
    Reorganize PDFs into year/month/day/language.pdf structure.

    Args:
        source_dir: Directory containing flat PDF files
        target_base: Base directory for reorganized structure
    """

    # Get all PDF files
    pdf_files = [f for f in os.listdir(source_dir) if f.endswith('.pdf')]
    pdf_files.sort()

    moved = 0
    skipped = 0
    errors = 0

    print(f"Found {len(pdf_files)} PDF files to reorganize")
    print(f"Source: {source_dir}")
    print(f"Target: {target_base}")
    print()

    for pdf_file in pdf_files:
        try:
            # Parse filename: YYYY-MM-DD_{language}_{index}.pdf
            parts = pdf_file.replace('.pdf', '').split('_')

            if len(parts) < 2:
                print(f"  SKIP (bad format): {pdf_file}")
                skipped += 1
                continue

            date_str = parts[0]  # YYYY-MM-DD
            language = parts[1]   # spanish or english

            # Parse date
            year, month, day = date_str.split('-')

            # Create target directory
            target_dir = Path(target_base) / year / month / day
            target_dir.mkdir(parents=True, exist_ok=True)

            # Target file: homilies/1977/03/14/spanish.pdf
            target_file = target_dir / f"{language}.pdf"
            source_file = Path(source_dir) / pdf_file

            # Check if target already exists
            if target_file.exists():
                print(f"  SKIP (exists): {target_file}")
                skipped += 1
                continue

            # Move file
            shutil.move(str(source_file), str(target_file))
            moved += 1

            if moved % 50 == 0 or moved == 1:
                print(f"[{moved}] Moved: {pdf_file} → {target_file}")

        except Exception as e:
            print(f"  ERROR processing {pdf_file}: {e}")
            errors += 1

    # Summary
    print()
    print("="*60)
    print("Reorganization Summary")
    print("="*60)
    print(f"Total PDFs: {len(pdf_files)}")
    print(f"Moved: {moved}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    print()
    print(f"New structure: {target_base}/{{year}}/{{month}}/{{day}}/{{language}}.pdf")


if __name__ == "__main__":
    import sys

    print("="*60)
    print("PDF Reorganizer")
    print("="*60)
    print()

    # Check if source directory exists
    if not os.path.exists('data/pdfs'):
        print("ERROR: data/pdfs directory not found")
        sys.exit(1)

    # Count PDFs
    pdf_count = len([f for f in os.listdir('data/pdfs') if f.endswith('.pdf')])
    if pdf_count == 0:
        print("ERROR: No PDF files found in data/pdfs/")
        sys.exit(1)

    print(f"Will reorganize {pdf_count} PDFs")
    print("From: data/pdfs/YYYY-MM-DD_language_index.pdf")
    print("To:   homilies/year/month/day/language.pdf")
    print()

    response = input("Continue? [y/N] ")
    if response.lower() != 'y':
        print("Cancelled")
        sys.exit(0)

    print()
    reorganize_pdfs()
