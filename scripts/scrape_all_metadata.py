#!/usr/bin/env python3
"""
Scrape all homily metadata from Romero Trust website.
This script collects data from both the index page and individual detail pages.
"""

import json
import sys
import os

# Add parent directory to path so we can import from collect-homilies
sys.path.insert(0, os.path.dirname(__file__))

# Import from collect-homilies module
import importlib.util
spec = importlib.util.spec_from_file_location("collect_homilies",
                                               os.path.join(os.path.dirname(__file__), "collect-homilies.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

get_homilies_from_index = module.get_homilies_from_index
add_detail_page_data = module.add_detail_page_data


if __name__ == "__main__":
    print("=" * 60)
    print("Romero Homilies Metadata Scraper")
    print("=" * 60)

    # Step 1: Get index data
    print("\n[1/2] Scraping index page...")
    homilies = get_homilies_from_index()
    print(f"✓ Found {len(homilies)} homilies")
    print(f"  Date range: {min(h['date'] for h in homilies)} to {max(h['date'] for h in homilies)}")
    print(f"  With audio: {sum(1 for h in homilies if h['has_audio'])}")

    # Step 2: Enrich with detail page data
    print(f"\n[2/2] Scraping detail pages (1 second delay between requests)...")
    print(f"      This will take approximately {len(homilies)} seconds (~{len(homilies)//60} minutes)")
    homilies = add_detail_page_data(homilies, delay=1.0)

    # Save results
    output_file = "archive/homilies_metadata.json"
    os.makedirs("data", exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(homilies, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved metadata to {output_file}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total homilies: {len(homilies)}")
    print(f"With Spanish titles: {sum(1 for h in homilies if h.get('spanish_title'))}")
    print(f"With English PDFs: {sum(1 for h in homilies if h.get('english_pdf_url'))}")
    print(f"With Spanish PDFs: {sum(1 for h in homilies if h.get('spanish_pdf_url'))}")
    print(f"With audio URLs: {sum(1 for h in homilies if h.get('audio_url'))}")

    # Check for any issues
    missing_spanish = [h for h in homilies if not h.get('spanish_pdf_url')]
    if missing_spanish:
        print(f"\n⚠ {len(missing_spanish)} homilies missing Spanish PDF:")
        for h in missing_spanish[:5]:
            print(f"  - {h['title']}")
        if len(missing_spanish) > 5:
            print(f"  ... and {len(missing_spanish) - 5} more")
