"""Load the user-editable Screener column mapping (canonical field name ->
actual CSV column header). Kept separate from artha.data.fields because the
vendor's exact column wording is discovered empirically per §13.4, not
something this codebase can assert on the vendor's behalf.
"""

from __future__ import annotations

import tomllib
from pathlib import Path


class FieldMapError(ValueError):
    """Raised when a field-map TOML file is missing or malformed."""


def load_field_map(path: str | Path, profile: str) -> dict[str, str]:
    """Return {canonical_name: csv_column_header} for one profile section.

    The TOML file has one table per profile, e.g.:

        [profile_1_standard]
        market_cap = "Market Capitalization"
        roce = "ROCE %"

    Missing file or missing profile section both return an empty mapping
    (a "we don't know yet" result) rather than raising, so callers can
    still run the column-ceiling check without a field map and simply get
    zero completeness rows.
    """
    map_path = Path(path)
    if not map_path.is_file():
        return {}

    try:
        raw = tomllib.loads(map_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise FieldMapError(f"invalid TOML in {map_path}: {exc}") from exc

    section = raw.get(profile, {})
    return {str(k): str(v) for k, v in section.items()}
