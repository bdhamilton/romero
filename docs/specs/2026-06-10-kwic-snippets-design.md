# Design: Keyword-in-Context (KWIC) Snippets

**Date:** 2026-06-10
**Status:** Approved
**Phase:** 2, item 2 ("Context snippets in drill-down")

## Motivation

When researching a topic across the corpus (e.g., mining homilies for references
to a theme), the chart tells you *where* a term clusters, but judging *relevance*
currently requires opening each PDF on the Romero Trust site. This feature shows
the sentence containing each match — original accents preserved, term
highlighted — directly in the drill-down, modeled on the concordance-style
retrieval of the Chesterton digital library (https://library.chesterton.org/).

## Decisions made

- **UI placement:** click-to-expand contexts inside the existing drill-down
  (month view and top-5 view). No dedicated concordance page for now.
- **Snippet unit:** the full sentence containing the match, capped at ~200
  characters on each side of the match for runaway sentences.
- **Volume:** show *all* matches in a homily when expanded (scrollable block),
  no pagination. Topical mining needs to scan everything.
- **Delivery:** a new on-demand endpoint (`/api/snippets`) fetched lazily per
  homily on first expand. `/api/search` is unchanged — search speed and payload
  stay exactly as today.

Rejected alternatives: embedding snippets in the search response (bloats and
slows every search to precompute contexts the user may never open); a
pre-split sentence table in the DB (schema change and rebuild step to solve a
performance problem a 188-document corpus doesn't have).

## Key enabling fact

The folded text columns (`{lang}_text_folded`) are character-for-character the
same length as the original text columns — verified across all 387 stored
texts. A regex match at offsets `[start, end)` in the folded text therefore
maps directly to the same offsets in the original, accented text. No
re-alignment logic is needed. (If the folding algorithm in
`scripts/build_search_index.py` ever changes, this invariant must be
re-verified; the test suite asserts it on sample data.)

## Components

### 1. `extract_snippets()` in `search.py`

```python
def extract_snippets(original_text, folded_text, pattern):
    """Return [{'text': str, 'highlights': [[start, end], ...]}, ...]"""
```

Algorithm:

1. `pattern.finditer(folded_text)` yields match offsets. The pattern is built
   by the existing `_build_pattern()`, so phrases, wildcards, and accent
   folding behave identically to `search_corpus()`.
2. Each match's offsets are applied to `original_text` (valid per the
   length-equality invariant above).
3. Expand each match to sentence boundaries in the original text:
   - **Backward:** to just after the previous `.`, `!`, `?`, or newline
     (paragraph break). A leading `¿` or `¡` adjacent to the sentence start is
     included.
   - **Forward:** to and including the next `.`, `!`, `?`, or to just before
     the next newline.
   - Strip leading/trailing whitespace from the result.
4. **Cap:** if a boundary lies more than 200 characters from the match edge,
   cut at the nearest word boundary inside the cap and add `…` on that side.
5. **Merge:** matches whose sentence spans overlap collapse into one snippet
   whose `highlights` list contains every match's range. Highlight offsets are
   relative to the snippet text.
6. Snippets are returned in document order.

Known limitation (documented, not solved): naive boundary detection splits on
abbreviations ("Mons.", "Sr.") occasionally, producing a short snippet.
Acceptable noise, same spirit as the Phase 0 footnote-marker decision.

### 2. `GET /api/snippets` in `app.py`

Query params:

| param | values | default | notes |
|---|---|---|---|
| `homily_id` | int | required | |
| `term` | string | required | same syntax as `/api/search` (phrases, `*` wildcards) |
| `lang` | `es` / `en` | `es` | invalid values fall back to `es`, matching `/api/search` |
| `accent_sensitive` | `0` / `1` | `0` | mirrors `search_corpus`'s normalization path exactly |

Behavior: load that homily's `{lang}_text` and `{lang}_text_folded`, build the
pattern with the same helpers `search_corpus` uses (`fold_accents`,
`tokenize_query`, `_build_pattern`), run `extract_snippets`, return:

```json
{
  "homily_id": 123,
  "term": "violencia",
  "count": 12,
  "snippets": [
    {"text": "…frente a la violencia institucionalizada…", "highlights": [[13, 22]]}
  ]
}
```

`count` is the total number of highlight ranges (not snippets), so it always
equals the per-homily count shown in the drill-down — same pattern, same text.

Errors:
- **400** — missing/empty `term`, or bare-wildcard term (same message as
  `search_corpus`'s existing rejection).
- **404** — unknown `homily_id`, or homily has no text in the requested
  language.

The endpoint returns offsets, not HTML; all escaping and `<mark>` wrapping
happens client-side. ~10ms of work per call (one regex pass over one
document); no server-side caching.

### 3. Frontend (`templates/ngram.html`)

- Every homily row in the drill-down (month view *and* top-5 view) gets a
  "show contexts ▸" toggle.
- First click: fetch `/api/snippets` with the row's homily id and the term,
  lang, and accent setting of the current search. Show an inline "loading…"
  state; on failure, an inline error message (row stays usable, retry on next
  click).
- Response cached in a JS map keyed by `homily_id|term|lang|accent_sensitive`;
  later clicks just toggle visibility ("hide contexts ▾").
- Rendering: HTML-escape snippet text, then wrap each highlight range in
  `<mark>` (apply ranges right-to-left so earlier offsets stay valid).
- Snippet list renders in a `max-height` scrollable block (~300px) under the
  row, styled consistently with the existing drill-down.
- API URL injected via `{{ url_for('api_snippets') | tojson }}`, per the
  project's `url_for()` convention (works at any mount path).

### 4. Edge cases

- **Multi-term searches:** drill-down lists are already per-term; each
  expansion requests only its own term. No change needed.
- **Accent-sensitive mode:** endpoint normalizes the term exactly as
  `search_corpus` does, so chart counts and snippet counts always agree.
- **Match at text start/end:** boundary scan clamps to text bounds.
- **Whole text is one "sentence"** (no punctuation): the 200-char cap handles
  it; snippet is ellipsized on both sides.

## Testing

New minimal suite: `tests/test_snippets.py`, pytest added to
`requirements.txt` (dev use; not imported by the app). Guarantees:

- `extract_snippets` — applying each highlight range to the snippet text
  yields a string the search pattern matches (e.g., searching `liberacion`
  highlights the accented "liberación" in the original).
- `extract_snippets` — total highlight count across snippets equals
  `search_corpus`'s count for the same text and term.
- `extract_snippets` — two matches in one sentence produce one snippet with
  two highlight ranges.
- `extract_snippets` — a 1,000-character unpunctuated stretch produces a
  capped snippet, ellipsized, cut at word boundaries.
- `extract_snippets` — phrase (`pueblo de dios`) and wildcard (`liber*`)
  patterns produce correctly-bounded highlights.
- `/api/snippets` (Flask test client) — 404 on unknown homily and on a homily
  missing the requested language; 400 on empty or bare-wildcard term;
  happy-path response whose `count` matches `/api/search`'s per-homily count
  for the same term.

No tests for template JS — it's DOM wiring around a fetch; verified by running
the app locally against known searches.

## Out of scope (natural follow-ons)

- Contexts in the CLI tool (`ngram.py`)
- A dedicated concordance page (flat passage list across the corpus)
- Exporting snippets (ties into Phase 2 export item)
- Smarter sentence segmentation (abbreviation handling)
