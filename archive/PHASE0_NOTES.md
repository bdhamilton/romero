# Phase 0: Text Extraction - COMPLETE ✓

## Summary
Successfully extracted and cleaned text from 358 PDFs (195 homilies, 1977-1980) using pdfplumber with comprehensive cleaning.

## Final Approach

### PDF Extraction Library: pdfplumber
- **Why pdfplumber**: Correctly handles multi-column PDF layouts, unlike PyPDF2
- **Alternative tested**: pdfminer.six (also works, but more complex API)
- **PyPDF2 issue**: Words run together without newlines in multi-column PDFs (e.g., "larica", "pastoralde")
- **pdfplumber advantage**: Zero run-together words - perfect column boundary detection

### Text Cleaning Pipeline

#### 1. Fix hyphenated words across line breaks
```python
text = re.sub(r'-\n', '', text)  # "herma-\nnos" → "hermanos"
```

#### 2. Add spaces where newlines separate words
```python
text = re.sub(r'([^\s])\n([^\s])', r'\1 \2', text)  # "Iglesia\nuniversal" → "Iglesia universal"
```

#### 3. Remove headers and footers
**Spanish headers** (middle pages):
- `‡ Ciclo C, 1977 ‡` - Running header indicating liturgical cycle
- `‡ Homilías de Monseñor Romero ‡` - Book title header

**English headers/footers**:
- `St Oscar Romero, [Title], [Date]` - Running header on every page
- `Read or listen to the homilies of St Oscar Romero at romerotrust.org.uk` - Footer on every page

#### 4. Remove page numbers
- Standalone numbers on their own lines: `\n\d+\s*\n`
- Numbers at end of lines: `\s+\d+\s*$`

#### 5. Normalize whitespace
- Replace tabs with spaces
- Multiple spaces → single space
- Remove spaces around newlines
- Multiple newlines → double newline

### Critical: Regex Order
```python
# 1. FIRST: Remove hyphens at line breaks
text = re.sub(r'-\n', '', text)

# 2. SECOND: Add spaces at newlines
text = re.sub(r'([^\s])\n([^\s])', r'\1 \2', text)

# 3. THIRD: Remove headers/footers/page numbers
# 4. FOURTH: Normalize whitespace
```

**Why order matters**: If you add spaces first, the hyphen pattern `-\nn` becomes `- n`, breaking hyphen removal.

## Results
- **Total PDFs processed**: 358
- **Extraction errors**: 0
- **Output location**: `data/homilies/{year}/{month}/{day}/{language}.txt`
- **Data quality**: Clean text with no headers, footers, page numbers, or run-together words
- **Preserved content**: Biblical references (EN 30, Mt 25:40), footnotes, and all homily text

## Files
- `scripts/extract_text.py`: Full corpus extraction
- `scripts/extract_samples.py`: Sample extraction for testing (4 files)
- `scripts/test_headers.py`: Header pattern verification across time periods

## Testing
Verified header/footer removal across multiple time periods:
- 1977 (early): Patterns consistent
- 1978 (mid): Patterns consistent
- 1979: Patterns consistent
- 1980 (late): Patterns consistent

All headers, footers, and page numbers successfully removed while preserving homily content.

## Next Steps
Phase 1: Database Design and Implementation
