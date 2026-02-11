#!/usr/bin/env python3
"""
One-time script to add the 2 homilies missing from the original scrape.

The Romero Trust index page has malformed HTML for these entries — their occasion
field uses the wrong CSS class (field-name-field-date instead of
field-name-field-homily-occasion), so the original scraper skipped them.

The scraper (01_scrape_all_metadata.py) has been fixed, but rather than re-running
the full pipeline, this script adds just these 2 entries:
  - 1977-03-20: The One Mass (La misa única)
  - 1977-04-07: Anointing of the Spirit (La unción del Espíritu)
"""

import os
import sys
import sqlite3
import re
import unicodedata
from pathlib import Path

import requests
import pdfplumber

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / 'romero.db'
HOMILIES_DIR = PROJECT_ROOT / 'homilies'

# The two missing homilies and all their metadata (verified from detail pages)
MISSING = [
    {
        'date': '1977-03-20',
        'occasion': 'Fourth Sunday in Lent',
        'english_title': 'The One Mass',
        'detail_url': 'https://www.romerotrust.org.uk/1977-homilies/one-mass/',
        'biblical_references': 'Luke 15:1-3, 11-32; Joshua 5:9, 10-12; 2 Corinthians 5:17-21',
        'english_pdf_url': 'https://www.romerotrust.org.uk/wp-content/uploads/ART_Homilies_Vol1_2_OneMass.pdf',
        'spanish_pdf_url': 'https://www.romerotrust.org.uk/wp-content/uploads/1977-03-20-La-misa-unica.pdf',
        'audio_url': 'https://romerotrust.b-cdn.net/homilia%2020%20marzo%201977.mp3?_=3',
    },
    {
        'date': '1977-04-07',
        'occasion': 'Chrism Mass - Holy Thursday',
        'english_title': 'Anointing of the Spirit',
        'detail_url': 'https://www.romerotrust.org.uk/1977-homilies/anointing-spirit/',
        'biblical_references': 'Luke 4:16-21; Isaiah 61:1-3a, 6a, 8b-9; Revelation 1:5-8',
        'english_pdf_url': 'https://www.romerotrust.org.uk/wp-content/uploads/ART_Homilies_Vol1_3_AnointingSpirit.pdf',
        'spanish_pdf_url': 'https://www.romerotrust.org.uk/wp-content/uploads/1977-04-07-La-uncion-del-Espirito.pdf',
        'audio_url': None,
    },
]


def clean_text(text):
    """Clean extracted PDF text (same logic as 03_extract_text.py)."""
    text = re.sub(r'-\n', '', text)
    text = re.sub(r'([^\s])\n([^\s])', r'\1 \2', text)
    text = re.sub(r'‡\s*Ciclo [ABC],\s*\d{4}\s*‡', '', text)
    text = re.sub(r'‡\s*Homilías de Monseñor Romero\s*‡', '', text)
    text = re.sub(r'St Oscar Romero,.*?(?:\d{1,2} [A-Z][a-z]+ \d{4}|\d+ [A-Z][a-z]+ \d{4})', '', text)
    text = re.sub(r'Read or listen to the homilies of St Oscar Romero at romerotrust\.org\.uk', '', text)
    text = re.sub(r'\n\d+\s*\n', '\n', text)
    text = re.sub(r'\s+\d+\s*$', '', text, flags=re.MULTILINE)
    text = text.replace('\t', ' ')
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n ', '\n', text)
    text = re.sub(r' \n', '\n', text)
    text = re.sub(r'\n\n\n+', '\n\n', text)
    return text.strip()


def fold_accents(text):
    """Strip diacritical marks for accent-insensitive matching."""
    decomposed = unicodedata.normalize('NFD', text)
    return ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')


def download_pdf(url, dest):
    """Download a PDF if it doesn't already exist."""
    if dest.exists():
        print(f"  Skip (exists): {dest}")
        return True
    print(f"  Downloading: {dest.name}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, 'wb') as f:
        f.write(resp.content)
    return True


def extract_text(pdf_path):
    """Extract and clean text from a PDF."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = [p.extract_text() for p in pdf.pages]
    return clean_text('\n\n'.join(p for p in pages if p))


def get_spanish_title(detail_url):
    """Scrape the Spanish title from a detail page (text of the Spanish PDF link)."""
    resp = requests.get(detail_url, timeout=30)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.content, 'html.parser')
    for link in soup.find_all('a', href=lambda x: x and '.pdf' in x.lower()):
        filename = link['href'].split('/')[-1]
        if filename[:4].isdigit():
            return link.get_text(strip=True)
    return None


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    for h in MISSING:
        date = h['date']
        year, month, day = date.split('-')
        homily_dir = HOMILIES_DIR / year / month / day

        # Check if already in DB
        cursor.execute('SELECT id FROM homilies WHERE detail_url = ?', (h['detail_url'],))
        if cursor.fetchone():
            print(f"\n{h['english_title']} ({date}) — already in database, skipping")
            continue

        print(f"\n{h['english_title']} ({date})")

        # 1. Download PDFs
        spanish_pdf_path = homily_dir / 'spanish.pdf'
        english_pdf_path = homily_dir / 'english.pdf'
        download_pdf(h['spanish_pdf_url'], spanish_pdf_path)
        download_pdf(h['english_pdf_url'], english_pdf_path)

        # 2. Extract text
        print("  Extracting text...")
        spanish_text = extract_text(spanish_pdf_path)
        english_text = extract_text(english_pdf_path)
        print(f"  Spanish: {len(spanish_text):,} chars, English: {len(english_text):,} chars")

        # 3. Get Spanish title from detail page
        spanish_title = get_spanish_title(h['detail_url'])
        print(f"  Spanish title: {spanish_title}")

        # 4. Pre-fold for search index
        spanish_folded = fold_accents(spanish_text).lower()
        spanish_word_count = len(re.findall(r'\w+', spanish_text.lower(), re.UNICODE))

        # 5. Insert into database
        cursor.execute('''
            INSERT INTO homilies (
                date, occasion, english_title, spanish_title,
                detail_url, biblical_references,
                spanish_pdf_url, spanish_pdf_path,
                english_pdf_url, english_pdf_path,
                spanish_text, english_text, audio_url,
                spanish_text_folded, spanish_word_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            date, h['occasion'], h['english_title'], spanish_title,
            h['detail_url'], h['biblical_references'],
            h['spanish_pdf_url'], str(spanish_pdf_path),
            h['english_pdf_url'], str(english_pdf_path),
            spanish_text, english_text, h['audio_url'],
            spanish_folded, spanish_word_count,
        ))
        print(f"  Inserted (id={cursor.lastrowid})")

    conn.commit()

    # Verify
    cursor.execute('SELECT COUNT(*) FROM homilies')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM homilies WHERE spanish_text IS NOT NULL')
    spanish = cursor.fetchone()[0]
    print(f"\nDatabase now has {total} homilies ({spanish} with Spanish text)")

    conn.close()


if __name__ == '__main__':
    main()
