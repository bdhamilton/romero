# Design: "Show all" in the post-search homily list

**Date:** 2026-06-17
**Status:** Approved
**Phase:** 2, item 4 ("UI polish and user experience improvements")

## Motivation

After a search, the drill-down area shows a "Top homilies" summary — the
homilies with the most occurrences of the term. This list is currently capped
at the top 10 (`showTopHomilies()` in `templates/ngram.html`). But a sustained
theme can be scattered across 40+ homilies, and a researcher mining the corpus
often wants to see *every* reference, not just the heaviest hitters. The cap
hides the long tail that frequency analysis is meant to surface.

The fix is cheap: `/api/search` already ships every matching homily for every
term to the browser. The top-10 limit is purely a display `.slice(0, 10)`, so
revealing the rest needs no new endpoint, query, or payload change.

## Decisions made

- **Scope:** frontend-only, confined to `showTopHomilies()` in
  `templates/ngram.html`. No changes to `app.py`, `search.py`, or any API.
- **Threshold:** when a term has **≤10** homilies, render exactly as today with
  no button. When **>10**, render the top 10 followed by a toggle button.
- **Button:** labeled `Show all N homilies ▾`, where N is that term's homily
  count (`all.length`, which equals `total_homilies` for the term).
- **Expansion:** clicking appends rows 11…N in place using the same
  `homilyRow()` markup, so every newly revealed row keeps its existing
  `show contexts ▸` toggle (lazy per-row KWIC fetch, unchanged).
- **Reversible:** after expanding, the button flips to `Show top 10 ▴` and
  collapses back to the top 10. Toggle, not a one-way reveal.
- **Sort order:** unchanged — homilies sorted by occurrence count descending,
  so the top 10 stay on top and the long tail follows.
- **Multi-term:** each term section gets its own list and its own button,
  scoped to that section. The existing per-term loop already isolates them.

Rejected alternatives:
- *Auto-expanding every context snippet on "show all"* — would fire ~40
  `/api/snippets` calls at once and produce a wall of highlighted text. The
  per-row `show contexts` toggle already lets users open contexts selectively.
- *A new "all references" endpoint or page* — unnecessary; the data is already
  client-side.

## Implementation notes

`showTopHomilies()` currently builds, per term:

```js
all.sort((a, b) => b.count - a.count);
const top = all.slice(0, 10);
// ... renders <ul> of top ...
```

The change: render the top 10 into the `<ul>` as now, and when `all.length > 10`
append a button after the list. The button's handler renders the remaining rows
(`all.slice(10)`) into the same `<ul>` and toggles its own label and the
visibility of the tail rows. Because the full `all` array is already in scope at
render time, no refetch is needed on toggle.

Implementation should follow the existing delegation pattern in the file (the
drill-down already uses a single delegated click listener on `#drilldown` for
the `show contexts` toggles). The "show all" button can reuse that delegated
listener or attach per-button — whichever stays closest to the existing code.

## Testing

This change is pure template JavaScript. The project's `tests/` suite is pytest
against Python (snippet extraction and the `/api/snippets` endpoint); there is
no JavaScript test harness in this repo. So this feature is **verified
manually** — no automated test is added, by deliberate choice:

- Search a high-frequency single term (e.g. `pueblo`): the "Top homilies"
  heading reports >10 homilies, exactly 10 rows show, and a
  `Show all N homilies ▾` button appears with N matching the heading's count.
- Click the button: rows 11…N appear, sorted by count after the top 10, and the
  button flips to `Show top 10 ▴`. Click again: collapses back to 10 rows.
- Expand a row revealed by "show all" and confirm its `show contexts ▸` toggle
  still loads KWIC snippets.
- Search a low-frequency term with ≤10 homilies: no button appears.
- Search a multi-term query (e.g. `pueblo, iglesia`): each term section has its
  own independent button reflecting its own homily count.
