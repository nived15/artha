"""Data spine (implementation_plan.md Phase 1, plan.md §13).

Screener.in Premium's CSV export is the sanctioned bulk fundamentals feed
(§13.2a) — human-triggered, capped at 50 columns per query (§13.4a). This
package provides:

- ``fields``: the canonical required-field spec used by the §13.4 validation
  spike to check column-ceiling and completeness against a real export.
- ``snapshot``: a content-addressable, immutable snapshot store with a
  staleness guard (§13.6).
- ``screener_import``: ingests a Screener export CSV and runs the §13.4
  spike checks against it.
- ``filings``: a citation-preserving (doc_id, page, text) chunk store for
  BSE filings, so every later dossier claim can cite an exact source.
"""
