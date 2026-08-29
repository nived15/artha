---
name: artha-dossier-json-schema
description: >-
  The exact JSON field names and shapes artha.dossier.validator.validate_dossier
  expects for a dossier draft — required reading before assembling a full
  dossier or any individual section for the artha-dossier factory.
license: MIT
---

# Dossier JSON schema (matches artha/dossier/schema.py exactly)

`validate_dossier` and `write_dossier` parse a JSON object with these exact
top-level keys. Field names are Python identifiers (snake_case) — do not
rename them, add extra nesting, or use section numbers as keys.

## Generic section shape (`DossierSection`)

Used for every narrative/evidence section:

```json
{"title": "...", "content": "...", "citations": [{"doc_id": "...", "page": 1, "note": "..."}]}
```

`citations` may be an empty array `[]`, but sections plan.md requires a
source citation for (financial_evidence, fatal_flaw_checklist, valuation,
margin_of_safety_scuttlebutt, scale_economies_shared,
magic_formula_attribution, conviction_sizing, davis_double_play,
quality_compounding_checklist, disconfirming_evidence, and the two gates)
will be **rejected** if `citations` is empty.

## Top-level keys

| Key | Shape | Dossier §  |
|---|---|---|
| `identity` | `{company, ticker, sector, arithmetic_profile, track, date, pipeline_run_id, snapshot_id}` (all strings; `track` is `"A"` or `"B"`) | §1 |
| `business_five_sentences` | `DossierSection` | §2 |
| `why_now` | `DossierSection` | §3 |
| `three_things_must_be_true` | `DossierSection` | §4 |
| `financial_evidence` | `DossierSection` (citations required) | §5 |
| `fatal_flaw_checklist` | `DossierSection` (citations required) | §6 |
| `valuation` | `DossierSection` (citations required) | §7 |
| `buy_below_and_sizing` | `DossierSection` | §8 |
| `pre_mortem` | `DossierSection` | §9 |
| `kill_triggers` | `DossierSection` | §10 |
| `what_would_make_me_add_more` | `DossierSection` | §11 |
| `disconfirming_evidence` | `DossierSection` (citations required; **content must not be empty**) | §12 |
| `holding_period_and_tax` | `DossierSection` | §13 |
| `provenance` | `{model, prompt_version, documents_read: [doc_id, ...], could_not_verify: [claim, ...]}` (`could_not_verify` may be `[]`, but the key must be present) | §14 |
| `moat_understandability_gate` | `{passed, moat_type, moat_evidence, return_trend_summary, five_sentence_test_result, understandability_checklist: {7 boolean keys}, inversion_summary, citations}` — **gate**, `passed: false` fails validation | §15 |
| `qglp_scorecard` | `{quality, growth, longevity, price (each 0-3 int), evidence: {"Q":..., "G":..., "L":..., "P":...}, citations}` | §16 |
| `margin_of_safety_scuttlebutt` | `DossierSection` (citations required) | §17 |
| `integrity_gate` | `{passed, promoter_pledge_flag, declining_holding_flag, rpt_or_auditor_or_sebi_flag, evidence, citations}` — **gate**, `passed: false` fails validation | §18 |
| `davis_double_play` | `DossierSection` or `null`/omitted — **required for Track B, must be omitted for Track A** | §19 |
| `scale_economies_shared` | `DossierSection` (citations required) | §20 |
| `magic_formula_attribution` | `DossierSection` (citations required) | §21 |
| `quality_compounding_checklist` | `DossierSection` or `null`/omitted — **required for Track A, must be omitted for Track B** | §22 |
| `conviction_sizing` | `DossierSection` (citations required) | §23 |
| `canslim_notes` | `DossierSection` or `null`/omitted — **required for Track B, must be omitted for Track A** | §24 |

## Common mistakes that fail validation

- Omitting `citations` (or leaving it empty) on a section plan.md requires
  evidence for — the table above marks which ones.
- Leaving `disconfirming_evidence.content` empty, or writing a token
  one-line dismissal instead of a genuine case against the thesis.
- Providing `davis_double_play`/`canslim_notes` for a Track A dossier, or
  `quality_compounding_checklist` for a Track B dossier — track-conditional
  sections must be `null` or omitted for the *other* track, not just left
  empty.
- Setting a gate's `passed` to `true` without it being genuinely earned —
  `validate_dossier` takes your word for `passed`, but a false `true` only
  defers the problem to a human reviewer catching a gate that shouldn't
  have passed; that human catching it is not a design failure, but getting
  the gate honestly right the first time is the goal.
