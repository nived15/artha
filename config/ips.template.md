# Investment Policy Statement — Artha

> Status: **DRAFT — not yet frozen.** Fill in every `TODO`, review it, then
> record the freeze date here and in `config/artha.toml`'s `ips.frozen_on`.
> plan.md §11 (Phase 0 exit criterion): "IPS exists" means this document is
> complete and frozen before the passive core is funded and before any
> active-sleeve purchase.

**Frozen on:** TODO (ISO date, e.g. 2025-01-15) — leave blank until true.

## 1. Goals

TODO — restate plan.md §1 in your own words, with your own numbers:
what you're actually trying to achieve, over what horizon, and the honest
caveat that the software changes throughput/discipline, not base rates
(plan.md §2).

## 2. Capital allocation

- Passive core: TODO % of investable assets (plan.md suggests ~80%), in
  which instruments, funded by TODO (date).
- Active sleeve starting size: TODO % (plan.md default: 5%), scaled only
  per the per-track scorecard rules in plan.md §9.
- Track A / Track B split within the active sleeve: see
  `config/artha.toml`'s `[sizing]` section — keep this document and that
  config in sync.

## 3. Benchmark (freeze once, never change)

TODO — the same values as `config/artha.toml`'s `[benchmark]` section,
restated here for the record: named Nifty 50 TR index fund + one named
factor fund, fixed weights (plan.md §9).

## 4. Sizing and hard limits

TODO — restate `config/artha.toml`'s `[sizing]` values and confirm you
accept them, or record deliberate deviations and why.

## 5. Sell discipline

TODO — restate plan.md §2.4's rule in your own words: winners are never
mechanically trimmed at 2x; sells are thesis-broken or valuation-driven
only. Nothing sold before 12 months unless the thesis is broken (§2.3).

## 6. Review cadence

TODO — when you will review the scorecard (plan.md §9's staged
graduation criteria) and what would make you shut a track down.

## 7. What would make you stop using this application entirely

TODO — plan.md §2.2's honest caveat, made personal: at what point does
underperformance mean the process itself has failed, not just a run of
bad luck?
