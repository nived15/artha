"""Dossier (implementation_plan.md Phase 2.5, plan.md §6).

"One markdown file per candidate, immutable once approved, versioned in
git... Sections 12 and 14 are the anti-self-deception mechanism. A
dossier missing either is rejected by the tooling, not by your
discipline." This package is the deterministic harness the agent layer
(Phase 3a) will write into and Phase 3's factory validates against — it
has no LLM dependency itself.

- ``schema``: the 24-section dossier data model (plus the two gate
  sections, §15/§18).
- ``validator``: completeness + citation-presence checker. Rejects,
  never warns — matching plan.md's own line.
- ``render``: renders a Dossier to the markdown format §6 specifies.
- ``storage``: writes the immutable markdown file (dossiers/<ticker>/
  <run_id>.md) and the queryable SQLite index row, per
  implementation_plan.md §16 Q1's "both" resolution.
"""
