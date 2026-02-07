#!/usr/bin/env python3
"""
Download all PDF files from Romero Trust website.
Uses metadata from homilies_metadata.json.
"""

import json
import os
import time
import requests
from pathlib import Path


def download_pdfs(metadata_file='data/homilies_metadata.json',
                  output_dir='data/pdfs',
                  delay=2.0):
    """
    Download all PDFs referenced in metadata.

    Args:
        metadata_file: Path to JSON file with homily metadata
        output_dir: Directory to save PDFs
        delay: Seconds between downloads (default 2.0)
    """

    # Load metadata
    with open(metadata_file, 'r') as f:
        homilies = json.load(f)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Count total PDFs to download
    total_pdfs = sum(
        (1 if h.get('spanish_pdf_url') else 0) +
        (1 if h.get('english_pdf_url') else 0)
        for h in homilies
    )

    print(f"Found {total_pdfs} PDFs to download")
    print(f"Output directory: {output_dir}")
    print(f"Rate limit: {delay} seconds between downloads")
    print()

    downloaded = 0
    skipped = 0
    errors = 0

    for idx, homily in enumerate(homilies):
        date = homily['date']

        # Download Spanish PDF
        if homily.get('spanish_pdf_url'):
            filename = f"{date}_spanish_{idx:03d}.pdf"
            filepath = os.path.join(output_dir, filename)

            if os.path.exists(filepath):
                print(f"[{downloaded + skipped + 1}/{total_pdfs}] Skip (exists): {filename}")
                skipped += 1
            else:
                if downloaded > 0:  # Rate limit (skip first)
                    time.sleep(delay)

                try:
                    print(f"[{downloaded + skipped + 1}/{total_pdfs}] Downloading: {filename}")
                    response = requests.get(homily['spanish_pdf_url'], timeout=30)
                    response.raise_for_status()

                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    downloaded += 1

                except Exception as e:
                    print(f"  ERROR: {e}")
                    errors += 1

        # Download English PDF
        if homily.get('english_pdf_url'):
            filename = f"{date}_english_{idx:03d}.pdf"
            filepath = os.path.join(output_dir, filename)

            if os.path.exists(filepath):
                print(f"[{downloaded + skipped + 1}/{total_pdfs}] Skip (exists): {filename}")
                skipped += 1
            else:
                if downloaded > 0:  # Rate limit
                    time.sleep(delay)

                try:
                    print(f"[{downloaded + skipped + 1}/{total_pdfs}] Downloading: {filename}")
                    response = requests.get(homily['english_pdf_url'], timeout=30)
                    response.raise_for_status()

                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    downloaded += 1

                except Exception as e:
                    print(f"  ERROR: {e}")
                    errors += 1

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
    print(f"PDFs saved to: {output_dir}")


if __name__ == "__main__":
    import sys

    # Check if metadata exists
    if not os.path.exists('data/homilies_metadata.json'):
        print("ERROR: data/homilies_metadata.json not found")
        print("Run scrape_all_metadata.py first")
        sys.exit(1)

    print("="*60)
    print("Romero Homilies PDF Downloader")
    print("="*60)
    print()

    # Estimate time
    with open('data/homilies_metadata.json', 'r') as f:
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
