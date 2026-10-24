"""Pull OpenAlex works by DOI and by grant award id."""

from __future__ import annotations

import hashlib
import json
import logging

import pandas as pd
import requests

from eu_impact.config import INTERIM, RAW, load_config, mailto, openalex_api_key
from eu_impact.http import CachedClient
from eu_impact.ids import normalize_doi, normalize_grant_id

log = logging.getLogger(__name__)

SELECT = ",".join(
    [
        "id",
        "doi",
        "type",
        "publication_date",
        "cited_by_count",
        "fwci",
        "citation_normalized_percentile",
        "open_access",
        "counts_by_year",
        "awards",
        "authorships",
    ]
)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not mailto():
        raise SystemExit("Set OPENALEX_MAILTO in .env before pulling OpenAlex.")
    config = load_config()
    ids = _pilot_ids()
    known_dois = _dois_by_project()
    client = CachedClient(pause_seconds=float(config["request_pause_seconds"]))
    base_url = config["openalex"]["base_url"]
    per_page = int(config["openalex"]["per_page"])
    batch_size = int(config["openalex"]["doi_batch_size"])
    rows: list[dict] = []

    for index, project_id in enumerate(ids, start=1):
        by_award = _by_award(client, base_url, project_id, per_page)
        found_dois = {row["doi"] for row in by_award if row["doi"]}
        missing = sorted(doi for doi in known_dois.get(project_id, set()) if doi not in found_dois)
        by_doi = _by_doi(client, base_url, project_id, missing, per_page, batch_size)
        merged = _dedupe(by_award + by_doi)
        log.info(
            "OpenAlex %s/%s %s -> %s works (%s by award, %s extra DOIs queried)",
            index,
            len(ids),
            project_id,
            len(merged),
            len(by_award),
            len(missing),
        )
        rows.extend(merged)

    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(
            columns=[
                "project_id",
                "openalex_id",
                "doi",
                "type",
                "publication_date",
                "cited_by_count",
                "fwci",
                "citation_percentile",
                "is_top10",
                "is_oa",
                "counts_by_year",
            ]
        )
    INTERIM.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(INTERIM / "openalex_works.parquet", index=False)
    log.info("wrote openalex_works.parquet (%s rows)", len(frame))


def _by_award(client: CachedClient, base_url: str, project_id: str, per_page: int) -> list[dict]:
    cursor = "*"
    seen: set[str] = set()
    rows: list[dict] = []
    for page in range(500):
        payload = fetch(
            client,
            base_url,
            {
                "filter": f"awards.funder_award_id:{project_id}",
                "per_page": per_page,
                "cursor": cursor,
                "select": SELECT,
            },
            RAW / "openalex" / project_id / f"awards_{page:03d}.json",
        )
        batch = payload.get("results") or []
        for work in batch:
            if _awarded_to(work, project_id):
                rows.append(_row(project_id, work))
        next_cursor = (payload.get("meta") or {}).get("next_cursor")
        if not batch or not next_cursor or next_cursor in seen:
            break
        seen.add(next_cursor)
        cursor = next_cursor
    return rows


def _by_doi(
    client: CachedClient,
    base_url: str,
    project_id: str,
    dois: list[str],
    per_page: int,
    batch_size: int,
) -> list[dict]:
    rows: list[dict] = []
    for batch in _batches(dois, batch_size):
        digest = hashlib.sha1(",".join(batch).encode()).hexdigest()[:12]
        values = "|".join(f"https://doi.org/{doi}" for doi in batch)
        payload = fetch(
            client,
            base_url,
            {"filter": f"doi:{values}", "per_page": per_page, "select": SELECT},
            RAW / "openalex" / project_id / f"dois_{digest}.json",
        )
        for work in payload.get("results") or []:
            rows.append(_row(project_id, work))
    return rows


def fetch(client: CachedClient, url: str, params: dict, cache) -> dict:
    params = dict(params)
    params["mailto"] = mailto()
    if openalex_api_key():
        params["api_key"] = openalex_api_key()
    try:
        return client.get_json(url, params, cache)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        body = exc.response.text[:400] if exc.response is not None else ""
        if status in {402, 403, 429}:
            raise SystemExit(
                f"OpenAlex refused the request ({status}). "
                "The shared daily budget may be spent. Set OPENALEX_API_KEY in .env and rerun. "
                "Pages already saved under data/raw/openalex are kept.\n"
                + body
            ) from exc
        raise


def _batches(dois: list[str], size: int) -> list[list[str]]:
    plain: list[str] = []
    batches: list[list[str]] = []
    for doi in dois:
        if any(char in doi for char in "|, "):
            batches.append([doi])
        else:
            plain.append(doi)
    for start in range(0, len(plain), size):
        batches.append(plain[start : start + size])
    return batches


def _awarded_to(work: dict, project_id: str) -> bool:
    for award in work.get("awards") or []:
        if isinstance(award, dict) and normalize_grant_id(award.get("funder_award_id")) == project_id:
            return True
    return False


def _row(project_id: str, work: dict) -> dict:
    percentile = work.get("citation_normalized_percentile") or {}
    if not isinstance(percentile, dict):
        percentile = {}
    access = work.get("open_access") or {}
    if not isinstance(access, dict):
        access = {}
    return {
        "project_id": project_id,
        "openalex_id": work.get("id"),
        "doi": normalize_doi(work.get("doi")),
        "type": work.get("type"),
        "publication_date": work.get("publication_date"),
        "cited_by_count": work.get("cited_by_count"),
        "fwci": work.get("fwci"),
        "citation_percentile": percentile.get("value"),
        "is_top10": percentile.get("is_in_top_10_percent"),
        "is_oa": access.get("is_oa"),
        "counts_by_year": json.dumps(work.get("counts_by_year") or []),
    }


def _dedupe(rows: list[dict]) -> list[dict]:
    found: dict[str, dict] = {}
    for row in rows:
        key = row["openalex_id"] or row["doi"] or str(id(row))
        found.setdefault(key, row)
    return list(found.values())


def _pilot_ids() -> list[str]:
    path = INTERIM / "pilot_ids.parquet"
    if not path.exists():
        raise SystemExit("Missing data/interim/pilot_ids.parquet. Run pull_cordis first.")
    return pd.read_parquet(path)["project_id"].astype(str).tolist()


def _dois_by_project() -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for name, column in (
        ("openaire_outputs.parquet", "doi"),
        ("zenodo_outputs.parquet", "doi"),
        ("cordis_publications.parquet", "doi"),
    ):
        path = INTERIM / name
        if not path.exists():
            raise SystemExit(f"Missing data/interim/{name}. Run the earlier pull steps first.")
        frame = pd.read_parquet(path)
        if frame.empty or "doi" not in frame.columns:
            continue
        for project_id, doi in frame[["project_id", column]].itertuples(index=False):
            if doi:
                grouped.setdefault(str(project_id), set()).add(str(doi))
    return grouped


if __name__ == "__main__":
    main()
