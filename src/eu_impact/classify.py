"""Map source-specific labels onto the output columns."""

from __future__ import annotations

import json
from datetime import date

_REVIEW = {"review", "review-article", "review article", "literature review"}


def timing(
    publication: date | None,
    start: date | None,
    end: date | None,
    precision: str = "day",
) -> str | None:
    """Class a publication as before, during, or after the project.

    ``precision="year"`` compares calendar years. A CORDIS row that only has
    ``publishedYear`` uses that, so 1 January is not treated as a real day.
    """
    if publication is None or start is None or end is None:
        return None
    if precision == "year":
        if publication.year < start.year:
            return "before"
        if publication.year > end.year:
            return "after"
        return "during"
    if publication < start:
        return "before"
    if publication > end:
        return "after"
    return "during"


def citations_in_window(counts_by_year: object, end: date | None, window_years: int) -> int | None:
    """Citations accrued by ``end.year + window_years``, from OpenAlex year counts."""
    if end is None:
        return None
    counts = _as_counts(counts_by_year)
    if not counts:
        return None
    horizon = end.year + window_years
    total = 0
    seen = False
    for item in counts:
        year = item.get("year")
        if year is None:
            continue
        if int(year) <= horizon:
            total += int(item.get("cited_by_count") or 0)
            seen = True
    if not seen:
        return None
    return total


def citations_excluding_self(counts_by_year: object, end: date | None, window_years: int) -> int | None:
    """Sum a known list of non-self citation counts through the horizon.

    ``None`` means the list was not pulled. An empty list is zero.
    """
    if end is None or counts_by_year is None:
        return None
    if isinstance(counts_by_year, float) and counts_by_year != counts_by_year:
        return None
    counts = _as_counts(counts_by_year)
    horizon = end.year + window_years
    total = 0
    for item in counts:
        year = item.get("year")
        if year is None:
            continue
        try:
            year = int(year)
        except (TypeError, ValueError):
            continue
        if year <= horizon:
            total += int(item.get("cited_by_count") or 0)
    return total


def is_top10(flag: object, percentile: object) -> bool | None:
    if isinstance(flag, bool):
        return flag
    if flag in {0, 1}:
        return bool(flag)
    if percentile is None:
        return None
    try:
        value = float(percentile)
    except (TypeError, ValueError):
        return None
    if value != value:  # NaN
        return None
    return value >= 0.9


def combined_output_type(labels: list[str], openalex_type: str | None = None) -> str:
    """Collapse source labels to article, review, dataset, software, or other."""
    cleaned = [(label or "").strip().lower() for label in labels]
    ox = (openalex_type or "").strip().lower()
    if ox == "review" or any(label in _REVIEW for label in cleaned):
        return "review"
    if ox == "dataset" or any(label == "dataset" for label in cleaned):
        return "dataset"
    if ox == "software" or any("software" in label for label in cleaned):
        return "software"
    if ox == "article" or any(
        label in {"publication", "article", "peer reviewed articles"} or "article" in label
        for label in cleaned
    ):
        return "article"
    if any(label for label in cleaned) or ox:
        return "other"
    return "other"


def _as_counts(value: object) -> list[dict]:
    if value is None:
        return []
    if isinstance(value, float) and value != value:
        return []
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []
