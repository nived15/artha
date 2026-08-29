---
name: artha-roiic-calculation
description: >-
  How to compute ROIIC (Return on Incremental Invested Capital) for the
  Scale Economies Shared Assessment (dossier §20). Triggers whenever an
  Artha agent needs to compute or explain ROIIC, or judge whether a
  candidate clears the "genuine compounder" threshold.
license: MIT
---

# Computing ROIIC (plan.md §5.5)

**ROIIC = ΔNOPAT ÷ ΔInvested Capital**, with a one-period lag: this year's
change in NOPAT divided by *last* year's change in invested capital (the
lag matters — new capital typically takes a period to start producing
returns, so comparing this year's ΔNOPAT to this year's ΔInvested Capital
understates the true return).

## Steps

1. **NOPAT** (Net Operating Profit After Tax) = EBIT × (1 − effective tax
   rate). Use the candidate's actual effective tax rate from cited filings,
   not a statutory assumption, if you can establish it.
2. **Invested Capital** = total debt + total equity − cash and cash
   equivalents (a standard proxy; note any adjustment you make, e.g. for
   goodwill, and why).
3. **ΔNOPAT** for year *t* = NOPAT(t) − NOPAT(t−1).
4. **ΔInvested Capital** for the lag period = Invested Capital(t−1) −
   Invested Capital(t−2).
5. **ROIIC(t)** = ΔNOPAT(t) ÷ ΔInvested Capital(t−1 lag).
6. Compute both a **3-year** and **5-year** window (average the annual
   ROIIC figures, or use the cumulative ΔNOPAT/ΔInvested-Capital over the
   window — state which method you used).

## Interpreting the result

- **ROIIC ≥ 25-30% is the "genuine compounder" threshold** (plan.md §5.5) —
  it means each incremental rupee of capital is generating an
  exceptionally high return, which is the quantitative companion to Sleep's
  qualitative "passing scale savings to customers" thesis: a company doing
  that can still compound at a high rate on its *incremental* capital even
  while giving up margin.
- A ROIIC below this threshold does not automatically fail the section —
  report it honestly either way, and let the qualitative
  volume-vs-price/management-language evidence carry the rest of the
  assessment.
- **If you cannot establish clean NOPAT/Invested-Capital inputs from cited
  filings, say so explicitly.** An estimated ROIIC built on guessed inputs
  is worse than reporting "insufficient data" — never present a fabricated
  number with false precision.
