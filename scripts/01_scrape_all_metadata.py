#!/usr/bin/env python3
"""
Scrape all homily metadata from Romero Trust website.
This script collects data from both the index page and individual detail pages.
"""

import json
import time
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime


def get_homilies_from_index():
    """
    Scrape the index page for basic homily metadata.

    Returns:
        List of dicts with occasion, title, url, date, has_audio, biblical_references
    """
    index_url = "https://www.romerotrust.org.uk/homilies-and-writing/homilies/"
    response = requests.get(index_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    homily_occasions = soup.find_all("div", class_="field-name-field-homily-occasion")

    homilies = []
    for occasion in homily_occasions:
        # Get data blocks for this homily
        title_block = occasion.find_next_sibling("div", class_="views-field-title")
        date_block = occasion.find_next_sibling("div", class_="field-name-field-date")

        # References might or might not exist; look for a <p> before the next occasion
        references_text = ""
        for sib in date_block.next_siblings:
            name = getattr(sib, "name", None)
            classes = (sib.get("class") or []) if name else []
            if name == "div" and "field-name-field-homily-occasion" in classes:
                break  # reached the next homily; stop
            if name == "p":
                references_text = sib.get_text(" ", strip=True).replace("\xa0", " ")
                break

        # Parse needed fields
        date_obj = datetime.strptime(date_block.get_text(strip=True), "%d %B %Y").date()

        # Check for audio
        has_audio = "AUDIO" in references_text

        # Try to remove audio indicators from references string
        for marker in ["(+AUDIO)", "(+ AUDIO)", "AUDIO"]:
            references_text = references_text.replace(marker, "")
        references_text = references_text.strip()

        homilies.append({
            "occasion": occasion.get_text(strip=True),
            "title": title_block.get_text(strip=True),
            "url": title_block.a["href"],
            "date": date_obj.isoformat(),
            "has_audio": has_audio,
            "biblical_references": references_text,
        })

    return homilies


def add_detail_page_data(homilies, delay=1.0):
    """
    Visit each homily's detail page to collect Spanish title and PDF URLs.

    Args:
        homilies: List of homily dicts from get_homilies_from_index()
        delay: Seconds to wait between requests (default 1.0)

    Returns:
        Enriched list of homily dicts
    """
    total = len(homilies)

    for i, homily in enumerate(homilies, 1):
        # Rate limiting
        if i > 1:
            time.sleep(delay)

        # Progress indicator
        if i % 10 == 0 or i == 1 or i == total:
            print(f"Processing {i}/{total}: {homily['title'][:50]}...")

        try:
            response = requests.get(homily['url'])
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all PDF links
            pdf_links = soup.find_all('a', href=lambda x: x and '.pdf' in x.lower())

            # Categorize PDFs
            english_pdf = None
            spanish_pdf = None
            spanish_title = None

            for link in pdf_links:
                url = link.get('href')
                filename = url.split('/')[-1]
                link_text = link.get_text(strip=True)

                if filename.startswith('ART_'):
                    english_pdf = url
                elif filename[:4].isdigit():  # Starts with year
                    spanish_pdf = url
                    spanish_title = link_text

            # Fallback to order if patterns didn't work
            if len(pdf_links) >= 1 and english_pdf is None:
                english_pdf = pdf_links[0].get('href')
            if len(pdf_links) >= 2 and spanish_pdf is None:
                spanish_pdf = pdf_links[1].get('href')
                spanish_title = pdf_links[1].get_text(strip=True)

            # Find audio URL (only if has_audio flag is True)
            audio_url = None
            if homily['has_audio']:
                audio_source = soup.find('source', src=lambda x: x and ('.mp3' in x.lower() or '.ogg' in x.lower()))
                if audio_source:
                    audio_url = audio_source.get('src')
                else:
                    audio_link = soup.find('a', href=lambda x: x and '.mp3' in x.lower())
                    if audio_link:
                        audio_url = audio_link.get('href')

            # Add to homily dict
            homily['spanish_title'] = spanish_title
            homily['english_pdf_url'] = english_pdf
            homily['spanish_pdf_url'] = spanish_pdf
            homily['audio_url'] = audio_url

        except Exception as e:
            print(f"  ERROR processing {homily['url']}: {e}")
            homily['spanish_title'] = None
            homily['english_pdf_url'] = None
            homily['spanish_pdf_url'] = None
            homily['audio_url'] = None

    print(f"\nCompleted processing {total} homilies")
    return homilies


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
    os.makedirs("archive", exist_ok=True)

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
