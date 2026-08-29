"""Phase 4 — paper ledger: tax lots, positions, and the post-tax scorecard.

plan.md §11 Phase 4: "Paper positions, tax lots, time/money-weighted
post-tax performance vs the frozen benchmark, per track. Gets real tests —
a silent bug here misleads you about your own record." Every trade this
package records is meant to be journaled by the caller (artha.journal),
matching every other phase's audit-trail discipline.
"""
