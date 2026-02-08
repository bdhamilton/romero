#!/usr/bin/env python3
"""
Debug script to test text cleaning regex on actual PyPDF2 output.
"""

import re
from PyPDF2 import PdfReader


# Extract a small sample from the actual PDF
pdf_path = 'data/homilies/1977/03/14/spanish.pdf'
reader = PdfReader(pdf_path)

# Get just the first page
page = reader.pages[0]
raw_text = page.extract_text()

print("=" * 60)
print("RAW PyPDF2 OUTPUT - looking for 'larica':")
print("=" * 60)

# Find the section with larica
import re
matches = re.finditer(r'.{50}larica.{50}', raw_text)
for match in matches:
    text = match.group()
    # Show with newlines visible
    text_visible = text.replace('\n', '⏎\n')
    print(text_visible)
    print()

print("=" * 60)
print("RAW PyPDF2 OUTPUT - looking for 'pastoralde':")
print("=" * 60)

matches = re.finditer(r'.{50}pastoralde.{50}', raw_text)
for match in matches:
    text = match.group()
    # Show with newlines visible
    text_visible = text.replace('\n', '⏎\n')
    print(text_visible)
    print()
