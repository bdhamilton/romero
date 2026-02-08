#!/usr/bin/env python3
"""
Download all PDF files from Romero Trust website directly into hierarchical structure.
Uses metadata from homilies_metadata.json.
Downloads to: homilies/{year}/{month}/{day}/{spanish|english}.pdf
"""

import json
import os
import time
import requests
from pathlib import Path


def download_pdfs(metadata_file='archive/homilies_metadata.json',
                  output_base='homilies',
                  delay=2.0):
    """
    Download all PDFs referenced in metadata into hierarchical structure.

    Args:
        metadata_file: Path to JSON file with homily metadata
        output_base: Base directory for hierarchical structure (default: homilies)
        delay: Seconds between downloads (default 2.0)
    """

    # Load metadata
    with open(metadata_file, 'r') as f:
        homilies = json.load(f)

    # Count total PDFs to download
    total_pdfs = sum(
        (1 if h.get('spanish_pdf_url') else 0) +
        (1 if h.get('english_pdf_url') else 0)
        for h in homilies
    )

    print(f"Found {total_pdfs} PDFs to download")
    print(f"Output structure: {output_base}/{{year}}/{{month}}/{{day}}/{{language}}.pdf")
    print(f"Rate limit: {delay} seconds between downloads")
    print()

    downloaded = 0
    skipped = 0
    errors = 0
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 3

    for idx, homily in enumerate(homilies):
        date = homily['date']  # Format: YYYY-MM-DD
        year, month, day = date.split('-')

        # Create directory for this homily
        homily_dir = Path(output_base) / year / month / day
        homily_dir.mkdir(parents=True, exist_ok=True)

        # Download Spanish PDF
        if homily.get('spanish_pdf_url'):
            filepath = homily_dir / 'spanish.pdf'

            if filepath.exists():
                print(f"[{downloaded + skipped + 1}/{total_pdfs}] Skip (exists): {year}/{month}/{day}/spanish.pdf")
                skipped += 1
            else:
                if downloaded > 0:  # Rate limit (skip first)
                    time.sleep(delay)

                try:
                    print(f"[{downloaded + skipped + 1}/{total_pdfs}] Downloading: {year}/{month}/{day}/spanish.pdf")
                    response = requests.get(homily['spanish_pdf_url'], timeout=30)
                    response.raise_for_status()

                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    downloaded += 1
                    consecutive_failures = 0  # Reset on success

                except Exception as e:
                    print(f"  ERROR: {e}")
                    errors += 1
                    consecutive_failures += 1

                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        print()
                        print("="*60)
                        print(f"STOPPING: {MAX_CONSECUTIVE_FAILURES} consecutive failures")
                        print("This may indicate a problem with the server or network.")
                        print("You can re-run this script to resume from where it left off.")
                        print("="*60)
                        print()
                        print(f"Downloaded so far: {downloaded}")
                        print(f"Errors: {errors}")
                        return

        # Download English PDF
        if homily.get('english_pdf_url'):
            filepath = homily_dir / 'english.pdf'

            if filepath.exists():
                print(f"[{downloaded + skipped + 1}/{total_pdfs}] Skip (exists): {year}/{month}/{day}/english.pdf")
                skipped += 1
            else:
                if downloaded > 0:  # Rate limit
                    time.sleep(delay)

                try:
                    print(f"[{downloaded + skipped + 1}/{total_pdfs}] Downloading: {year}/{month}/{day}/english.pdf")
                    response = requests.get(homily['english_pdf_url'], timeout=30)
                    response.raise_for_status()

                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    downloaded += 1
                    consecutive_failures = 0  # Reset on success

                except Exception as e:
                    print(f"  ERROR: {e}")
                    errors += 1
                    consecutive_failures += 1

                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        print()
                        print("="*60)
                        print(f"STOPPING: {MAX_CONSECUTIVE_FAILURES} consecutive failures")
                        print("This may indicate a problem with the server or network.")
                        print("You can re-run this script to resume from where it left off.")
                        print("="*60)
                        print()
                        print(f"Downloaded so far: {downloaded}")
                        print(f"Errors: {errors}")
                        return

    # Summary
    print()
    print("="*60)
    print("Download Summary")
    print("="*60)
    print(f"Total PDFs: {total_pdfs}")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped (already exist): {skipped}")
    print(f"Errors: {errors}")
    print()
    print(f"PDFs saved to: {output_base}/{{year}}/{{month}}/{{day}}/{{language}}.pdf")


if __name__ == "__main__":
    import sys

    # Check if metadata exists
    if not os.path.exists('archive/homilies_metadata.json'):
        print("ERROR: archive/homilies_metadata.json not found")
        print("Run scrape_all_metadata.py first")
        sys.exit(1)

    print("="*60)
    print("Romero Homilies PDF Downloader")
    print("="*60)
    print()

    # Estimate time
    with open('archive/homilies_metadata.json', 'r') as f:
        homilies = json.load(f)

    pdf_count = sum(
        (1 if h.get('spanish_pdf_url') else 0) +
        (1 if h.get('english_pdf_url') else 0)
        for h in homilies
    )

    estimated_minutes = (pdf_count * 2) // 60  # 2 seconds per PDF

    print(f"Will download ~{pdf_count} PDFs")
    print(f"Estimated time: ~{estimated_minutes} minutes")
    print()

    response = input("Continue? [y/N] ")
    if response.lower() != 'y':
        print("Cancelled")
        sys.exit(0)

    print()
    download_pdfs()
