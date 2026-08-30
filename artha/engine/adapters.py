"""Adapters from the Phase 1 data spine into engine features.

Deliberately reads the existing config/screener_field_map.toml rather than
introducing a second mapping file, so the new engine and the legacy screening
path stay on one source of truth while the old path is retired.
"""

from __future__ import annotations

from artha.engine.features import FEATURES, FeatureVector, build_feature_vector

# The v1 canonical names carry unit suffixes that the engine encodes in
# FeatureSpec.unit instead. Map the old names onto the new ones so existing
# field maps keep working untouched.
ENGINE_FROM_LEGACY: dict[str, str] = {
    "promoter_holding_pct": "promoter_holding",
    "promoter_pledge_pct": "promoter_pledge",
    "dividend_yield_pct": "dividend_yield",
    "fcf_conversion_pct": "fcf_conversion",
}

_PLACEHOLDER_PREFIX = "<"
_STRIP_CHARS = "%, \t\n\r"


def is_placeholder(column: str) -> bool:
    """A `<TODO: ...>` entry means unmapped, not a column literally named that."""
    return column.strip().startswith(_PLACEHOLDER_PREFIX)


def resolve_columns(field_map: dict[str, str]) -> dict[str, str]:
    """Return {engine_feature_name: csv_column} for mappings the engine can use."""
    resolved: dict[str, str] = {}
    for legacy_name, column in field_map.items():
        if not column or is_placeholder(column):
            continue
        engine_name = ENGINE_FROM_LEGACY.get(legacy_name, legacy_name)
        if engine_name in FEATURES:
            resolved[engine_name] = column
    return resolved


def parse_number(raw: str | None) -> float | str | None:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    cleaned = text.strip(_STRIP_CHARS).replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return text


def feature_vectors_from_rows(
    rows: list[dict[str, str]],
    field_map: dict[str, str],
    *,
    profile: str,
    as_of: str,
    name_column: str = "Name",
) -> list[FeatureVector]:
    """Build one FeatureVector per snapshot row. Rows without a name are skipped."""
    columns = resolve_columns(field_map)
    vectors: list[FeatureVector] = []
    for row in rows:
        ticker = (row.get(name_column) or "").strip()
        if not ticker:
            continue
        raw = {
            feature: parse_number(row.get(column))
            for feature, column in columns.items()
            if column in row
        }
        vectors.append(
            build_feature_vector(ticker=ticker, profile=profile, as_of=as_of, raw=raw)
        )
    return vectors


def coverage_report(vectors: list[FeatureVector]) -> dict[str, float]:
    """Share of the universe that has each feature, best-first.

    This is the diagnostic the v1 pipeline lacked: when nothing ranks, it
    shows immediately whether the cause is data coverage or company quality.
    """
    if not vectors:
        return {}
    counts = {name: 0 for name in FEATURES}
    for fv in vectors:
        for name in FEATURES:
            if name in fv.values:
                counts[name] += 1
    total = len(vectors)
    return dict(sorted(((n, c / total) for n, c in counts.items()), key=lambda kv: -kv[1]))
