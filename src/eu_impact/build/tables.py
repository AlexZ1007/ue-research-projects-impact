"""Build the four Parquet tables from the interim pulls."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import pandas as pd

from eu_impact.classify import (
    citations_excluding_self,
    citations_in_window,
    combined_output_type,
    is_top10,
    timing,
)
from eu_impact.config import INTERIM, PROCESSED, load_config

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config()
    window = int(config["citation_window_years"])
    projects = pd.read_parquet(INTERIM / "cordis_projects.parquet")
    organisations = pd.read_parquet(INTERIM / "cordis_organisations.parquet")
    pieces = _pieces()
    ends = {
        str(row.project_id): _as_date(row.end_date)
        for row in projects.itertuples(index=False)
    }
    starts = {
        str(row.project_id): _as_date(row.start_date)
        for row in projects.itertuples(index=False)
    }
    grouped: dict[str, list[dict]] = {}
    for piece in pieces:
        grouped.setdefault(_key(piece), []).append(piece)

    excl = _excl_counts()
    output_rows = [_merge(rows, starts, ends, window, excl) for rows in grouped.values()]
    outputs = pd.DataFrame(output_rows)
    if outputs.empty:
        outputs = pd.DataFrame(columns=_OUTPUT_COLUMNS)
    metrics = _metrics(projects, organisations, outputs)
    outputs = outputs.drop(columns=["is_top10"], errors="ignore")

    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    projects = projects.copy()
    organisations = organisations.copy()
    projects["retrieved_at"] = retrieved_at
    organisations["retrieved_at"] = retrieved_at
    outputs["retrieved_at"] = retrieved_at
    metrics["retrieved_at"] = retrieved_at
    for column in (
        "cited_by_count",
        "citations_in_window",
        "citations_excl_self",
        "zenodo_views",
        "zenodo_downloads",
    ):
        outputs[column] = _as_int(outputs[column])
    for column in ("citations_in_window", "citations_excl_self", "zenodo_views", "zenodo_downloads"):
        metrics[column] = _as_int(metrics[column])

    PROCESSED.mkdir(parents=True, exist_ok=True)
    projects.to_parquet(PROCESSED / "projects.parquet", index=False)
    organisations.to_parquet(PROCESSED / "organisations.parquet", index=False)
    outputs.to_parquet(PROCESSED / "outputs.parquet", index=False)
    metrics.to_parquet(PROCESSED / "project_metrics.parquet", index=False)
    log.info(
        "wrote projects=%s organisations=%s outputs=%s metrics=%s",
        len(projects),
        len(organisations),
        len(outputs),
        len(metrics),
    )


_OUTPUT_COLUMNS = [
    "project_id",
    "doi",
    "openalex_id",
    "output_type",
    "publication_date",
    "timing",
    "cited_by_count",
    "citations_in_window",
    "citations_excl_self",
    "fwci",
    "citation_percentile",
    "is_oa",
    "is_review",
    "zenodo_views",
    "zenodo_downloads",
    "sources",
]


def _excl_counts() -> dict[str, object]:
    path = INTERIM / "openalex_citations.parquet"
    if not path.exists():
        raise SystemExit(
            "Missing data/interim/openalex_citations.parquet. Run eu_impact.pull.citations first."
        )
    frame = pd.read_parquet(path)
    return {str(row.openalex_id): row.counts_excl_self for row in frame.itertuples(index=False)}


def _excl_value(raw, end, window: int):
    if raw is None or (not isinstance(raw, (str, list)) and pd.isna(raw)):
        return None
    return citations_excluding_self(raw, end, window)


def _pieces() -> list[dict]:
    rows: list[dict] = []
    rows.extend(_from_cordis(pd.read_parquet(INTERIM / "cordis_publications.parquet")))
    rows.extend(_from_openaire(pd.read_parquet(INTERIM / "openaire_outputs.parquet")))
    rows.extend(_from_zenodo(pd.read_parquet(INTERIM / "zenodo_outputs.parquet")))
    rows.extend(_from_openalex(pd.read_parquet(INTERIM / "openalex_works.parquet")))
    return rows


def _from_cordis(frame: pd.DataFrame) -> list[dict]:
    rows = []
    if frame.empty:
        return rows
    for record in frame.itertuples(index=False):
        year = record.published_year
        publication = None
        precision = "day"
        if not pd.isna(year):
            publication = date(int(year), 1, 1)
            precision = "year"
        rows.append(
            _blank(
                project_id=str(record.project_id),
                doi=_text(record.doi),
                source="cordis",
                source_id=_text(record.source_id) or _text(record.doi) or "",
                output_type=combined_output_type([_text(record.kind) or ""]),
                publication_date=publication,
                precision=precision,
            )
        )
    return rows


def _from_openaire(frame: pd.DataFrame) -> list[dict]:
    rows = []
    if frame.empty:
        return rows
    for record in frame.itertuples(index=False):
        publication, precision = _parse_date(record.publication_date)
        rows.append(
            _blank(
                project_id=str(record.project_id),
                doi=_text(record.doi),
                source="openaire",
                source_id=_text(record.source_id) or "",
                output_type=_text(record.output_type) or "other",
                publication_date=publication,
                precision=precision,
                is_oa=_bool(record.is_oa),
            )
        )
    return rows


def _from_zenodo(frame: pd.DataFrame) -> list[dict]:
    rows = []
    if frame.empty:
        return rows
    for record in frame.itertuples(index=False):
        publication, precision = _parse_date(record.publication_date)
        rows.append(
            _blank(
                project_id=str(record.project_id),
                doi=_text(record.doi),
                source="zenodo",
                source_id=_text(record.source_id) or "",
                output_type=_text(record.output_type) or "other",
                publication_date=publication,
                precision=precision,
                is_oa=True,
                zenodo_views=_number(record.zenodo_views),
                zenodo_downloads=_number(record.zenodo_downloads),
            )
        )
    return rows


def _from_openalex(frame: pd.DataFrame) -> list[dict]:
    rows = []
    if frame.empty:
        return rows
    for record in frame.itertuples(index=False):
        publication, precision = _parse_date(record.publication_date)
        work_type = _text(record.type)
        rows.append(
            _blank(
                project_id=str(record.project_id),
                doi=_text(record.doi),
                source="openalex",
                source_id=_text(record.openalex_id) or "",
                output_type=combined_output_type([], openalex_type=work_type),
                publication_date=publication,
                precision=precision,
                openalex_id=_text(record.openalex_id),
                cited_by_count=_number(record.cited_by_count),
                fwci=_number(record.fwci),
                citation_percentile=_number(record.citation_percentile),
                is_top10=_bool(record.is_top10),
                is_oa=_bool(record.is_oa),
                counts_by_year=record.counts_by_year,
            )
        )
    return rows


def _blank(**kwargs) -> dict:
    row = {
        "project_id": None,
        "doi": None,
        "source": None,
        "source_id": "",
        "output_type": "other",
        "publication_date": None,
        "precision": "day",
        "openalex_id": None,
        "cited_by_count": None,
        "fwci": None,
        "citation_percentile": None,
        "is_top10": None,
        "is_oa": None,
        "zenodo_views": None,
        "zenodo_downloads": None,
        "counts_by_year": None,
    }
    row.update(kwargs)
    return row


def _key(row: dict) -> str:
    if row["doi"]:
        return f"{row['project_id']}|doi|{row['doi']}"
    return f"{row['project_id']}|{row['source']}|{row['source_id']}"


def _merge(rows: list[dict], starts: dict, ends: dict, window: int, excl: dict) -> dict:
    openalex = next((row for row in rows if row["source"] == "openalex"), None)
    publication, precision = _prefer_date(rows)
    project_id = rows[0]["project_id"]
    output_type = _prefer_type(rows, openalex)
    percentile = _first(rows, "citation_percentile")
    top10 = openalex["is_top10"] if openalex and openalex["is_top10"] is not None else None
    if top10 is None:
        top10 = is_top10(None, percentile)
    counts = openalex["counts_by_year"] if openalex else None
    return {
        "project_id": project_id,
        "doi": rows[0]["doi"],
        "openalex_id": openalex["openalex_id"] if openalex else None,
        "output_type": output_type,
        "publication_date": publication,
        "timing": timing(publication, starts.get(project_id), ends.get(project_id), precision),
        "cited_by_count": _first(rows, "cited_by_count"),
        "citations_in_window": citations_in_window(counts, ends.get(project_id), window),
        "citations_excl_self": _excl_value(
            excl.get(openalex["openalex_id"]) if openalex and openalex["openalex_id"] else None,
            ends.get(project_id),
            window,
        ),
        "fwci": _first(rows, "fwci"),
        "citation_percentile": percentile,
        "is_oa": _merge_oa(rows),
        "is_review": output_type == "review",
        "zenodo_views": _max_number(rows, "zenodo_views"),
        "zenodo_downloads": _max_number(rows, "zenodo_downloads"),
        "sources": "|".join(sorted({row["source"] for row in rows})),
        "is_top10": top10,
    }


def _prefer_type(rows: list[dict], openalex: dict | None) -> str:
    types = {row["output_type"] for row in rows}
    if "review" in types:
        return "review"
    if openalex and openalex["output_type"] != "other":
        return openalex["output_type"]
    for name in ("dataset", "software", "article"):
        if name in types:
            return name
    return "other"


def _prefer_date(rows: list[dict]) -> tuple[date | None, str]:
    dated = [row for row in rows if row["publication_date"] is not None]
    days = [row for row in dated if row["precision"] == "day"]
    pool = days or dated
    if not pool:
        return None, "day"
    openalex = [row for row in pool if row["source"] == "openalex"]
    chosen = openalex[0] if openalex else pool[0]
    return chosen["publication_date"], chosen["precision"]


def _merge_oa(rows: list[dict]) -> bool | None:
    flags = [row["is_oa"] for row in rows if row["is_oa"] is not None]
    if not flags:
        return None
    return any(flags)


def _first(rows: list[dict], column: str):
    for row in rows:
        if row[column] is not None:
            return row[column]
    return None


def _max_number(rows: list[dict], column: str):
    values = [row[column] for row in rows if row[column] is not None]
    if not values:
        return None
    return max(values)


def _metrics(projects: pd.DataFrame, organisations: pd.DataFrame, outputs: pd.DataFrame) -> pd.DataFrame:
    org_groups = {str(project_id): group for project_id, group in organisations.groupby("project_id")}
    out_groups = {str(project_id): group for project_id, group in outputs.groupby("project_id")} if not outputs.empty else {}
    rows = []
    for project in projects.itertuples(index=False):
        project_id = str(project.project_id)
        group = out_groups.get(project_id, outputs.iloc[0:0])
        orgs = org_groups.get(project_id, organisations.iloc[0:0])
        papers = group[group["output_type"].isin(["article", "review"])] if not group.empty else group
        reviews_out = group[~group["is_review"]] if not group.empty else group
        rows.append(
            {
                "project_id": project_id,
                "n_outputs": int(len(group)),
                "n_articles": int((group["output_type"] == "article").sum()) if len(group) else 0,
                "n_reviews": int((group["output_type"] == "review").sum()) if len(group) else 0,
                "n_datasets": int((group["output_type"] == "dataset").sum()) if len(group) else 0,
                "n_software": int((group["output_type"] == "software").sum()) if len(group) else 0,
                "mean_fwci": _mean(group, "fwci"),
                "mean_fwci_excl_reviews": _mean(reviews_out, "fwci"),
                "pct_top10": _share_top(group),
                "pct_top10_excl_reviews": _share_top(reviews_out),
                "n_countries": int(orgs["country"].replace("", pd.NA).nunique(dropna=True)) if len(orgs) else 0,
                "n_organisations": int(orgs["organisation_id"].nunique(dropna=True)) if len(orgs) else 0,
                "zenodo_views": _sum(group, "zenodo_views"),
                "zenodo_downloads": _sum(group, "zenodo_downloads"),
                "n_outputs_per_million_eur": _per_million(len(group), project.ec_contribution),
                "citations_in_window": _sum(group, "citations_in_window"),
                "citations_in_window_per_million_eur": _per_million(
                    _sum(group, "citations_in_window"), project.ec_contribution
                ),
                "pct_oa": _share_true(papers, "is_oa"),
                "n_outputs_during": int((group["timing"] == "during").sum()) if len(group) else 0,
                "n_outputs_after": int((group["timing"] == "after").sum()) if len(group) else 0,
                "n_outputs_before": int((group["timing"] == "before").sum()) if len(group) else 0,
                "citations_excl_self": _sum(group, "citations_excl_self"),
            }
        )
    return pd.DataFrame(rows)


def _mean(frame: pd.DataFrame, column: str):
    if frame.empty or column not in frame:
        return None
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.mean())


def _as_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").round().astype("Int64")


def _sum(frame: pd.DataFrame, column: str):
    if frame.empty or column not in frame:
        return None
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.sum())


def _share_top(frame: pd.DataFrame):
    if frame.empty:
        return None
    flags = frame["is_top10"].map(_bool)
    known = [flag for flag in flags if flag is not None]
    if known:
        return sum(known) / len(known)
    percentiles = pd.to_numeric(frame["citation_percentile"], errors="coerce").dropna()
    if percentiles.empty:
        return None
    return float((percentiles >= 0.9).mean())


def _share_true(frame: pd.DataFrame, column: str):
    if frame.empty or column not in frame:
        return None
    flags = [flag for flag in frame[column].map(_bool) if flag is not None]
    if not flags:
        return None
    return sum(flags) / len(flags)


def _per_million(value, contribution):
    if value is None or pd.isna(contribution):
        return None
    contribution = float(contribution)
    if contribution <= 0:
        return None
    return float(value) * 1_000_000 / contribution


def _text(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "<na>"}:
        return None
    return text


def _number(value):
    if value is None or pd.isna(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _bool(value) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        if value.strip().lower() == "true":
            return True
        if value.strip().lower() == "false":
            return False
        return None
    return bool(value)


def _parse_date(value) -> tuple[date | None, str]:
    text = _text(value)
    if text is None:
        return None, "day"
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date(), "day" if len(text) >= 10 else "year"
    except ValueError:
        if text[:4].isdigit():
            return date(int(text[:4]), 1, 1), "year"
        return None, "day"


def _as_date(value) -> date | None:
    if value is None or pd.isna(value):
        return None
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        return None
    return parsed.date()


if __name__ == "__main__":
    main()
