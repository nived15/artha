"""Screening (implementation_plan.md Phase 2, plan.md §5.3-§5.4).

Deterministic Python, fully unit-testable — no LLM judgment belongs here
beyond the one pledging exception plan.md §13.3a already carves out (and
which Phase 1's validation spike found *is* now an automatable field, see
docs/phase1_validation_spike.md).

Scope boundary, following plan.md §13's own Stage 1a/1b split: this
package implements the **Stage 1a** checks — thresholds and ratios
computable from a single snapshot row (Phase 1's data spine) — plus the
Stage 2 hard blocks that are similarly single-row computable. Checks that
plan.md §13 itself assigns to **Stage 1b** (multi-year own-history
comparisons: sustained ROE/ROIC over 10 years, 10-year earnings-deficit
and dividend record, Davis's own-5-year P/E tercile) or to **Stage 3**
(qualitative LLM judgment: scuttlebutt, five-sentence business test,
promoter aspiration/TAM) are represented as an explicit
``needs_stage_1b``/``needs_stage_3`` outcome rather than silently
defaulted — the point of §5.4's "any unknown ends the analysis" is that a
gap must be visible, never guessed at.
"""
