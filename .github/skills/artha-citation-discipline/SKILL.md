---
name: artha-citation-discipline
description: >-
  The mandatory citation rule every Artha dossier-writing agent must follow:
  every factual claim needs a (doc_id, page) citation fetched via
  get_filing_chunk, uncited claims are defects not shortcuts, and unknowns
  fail closed rather than defaulting to a pass. Triggers whenever an Artha
  agent is writing dossier content, scoring a framework section, or
  verifying citations.
license: MIT
---

# Citation discipline (plan.md §5.5, §6)

This is Artha's non-negotiable evidence rule, shared by every dossier
section:

1. **Every figure, claim, or assertion needs a source citation** — a
   `(doc_id, page[, chunk_index])` you actually fetched with
   `get_filing_chunk`, not one you're inferring exists. "I recall that..."
   or "typically these companies..." is not a citation.
2. **An uncited claim is a defect, not an acceptable shortcut.** If you
   cannot find supporting evidence, say so explicitly ("could not verify
   X") rather than writing the claim anyway. `artha.dossier.validator`
   mechanically rejects sections that plan.md requires citations for and
   have none — there is no way to talk your way past this check, so don't
   try to satisfy it by inventing a plausible-looking citation.
3. **Unknowns fail closed, not open.** For anything plan.md treats as a
   disqualifying/gating question (promoter pledging, integrity red flags,
   the understandability gate), an unresolvable "unknown" is treated the
   same as a "no" — it does **not** default to a pass. This is explicit in
   plan.md §5.4: "Any 'no' or 'unknown' ends the analysis."
4. **Report what you could not verify — do not paper over gaps.** The
   dossier's Provenance section (§14) exists specifically to record this.
   An honest "could not verify" is more valuable than a confident-sounding
   guess; it is also directly checked by the completeness validator.
5. **You are not the only check.** A distinct citation-verification pass
   (the Artha Citation Verifier agent) will adversarially re-check your
   citations, and the deterministic `validate_dossier` tool is the final,
   non-negotiable backstop for completeness and citation-presence
   (implementation_plan.md §4/§8: "An LLM red-team is not independent
   evidence" — keep that gate regardless of how much verification runs
   before it).
