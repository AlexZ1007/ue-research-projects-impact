"""Pull Zenodo records linked to the pilot grants."""

from __future__ import annotations

import logging
import re

import pandas as pd

from eu_impact.classify import combined_output_type
from eu_impact.config import INTERIM, RAW, load_config
from eu_impact.http import CachedClient
from eu_impact.ids import normalize_doi

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config()
    ids = _pilot_ids()
    client = CachedClient(pause_seconds=float(config["request_pause_seconds"]))
    base_url = config["zenodo"]["base_url"]
    page_size = int(config["zenodo"]["page_size"])
    funder = config["zenodo"]["ec_funder"]
    rows: list[dict] = []

    for index, project_id in enumerate(ids, start=1):
        hits = _records(client, base_url, project_id, page_size, funder)
        log.info("Zenodo %s/%s %s -> %s records", index, len(ids), project_id, len(hits))
        rows.extend(hits)

    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(
            columns=[
                "project_id",
                "source_id",
                "doi",
                "output_type",
                "publication_date",
                "zenodo_views",
                "zenodo_downloads",
                "query",
            ]
        )
    INTERIM.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(INTERIM / "zenodo_outputs.parquet", index=False)
    log.info("wrote zenodo_outputs.parquet (%s rows)", len(frame))


def _records(client: CachedClient, base_url: str, project_id: str, page_size: int, funder: str) -> list[dict]:
    queries = [
        f"grants.code:{project_id}",
        f"metadata.grants.code:{project_id}",
        f'grants.internal_id:"{funder}::{project_id}"',
    ]
    found: dict[str, dict] = {}
    for query in queries:
        for hit, used_query in _pages(client, base_url, project_id, page_size, query):
            record_id = str(hit.get("id"))
            row = _row(project_id, hit, used_query)
            current = found.get(record_id)
            if current is None:
                found[record_id] = row
            elif used_query not in current["query"].split("|"):
                current["query"] = current["query"] + "|" + used_query
    return list(found.values())


def _pages(client: CachedClient, base_url: str, project_id: str, page_size: int, query: str):
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", query)[:90]
    for page in range(1, 400):
        cache = RAW / "zenodo" / project_id / f"{slug}_page_{page:03d}.json"
        payload = client.get_json(base_url, {"q": query, "size": page_size, "page": page}, cache)
        hits_block = payload.get("hits") or {}
        hits = hits_block.get("hits") or []
        if page == 1 and _total(hits_block) == 0:
            return
        for hit in hits:
            yield hit, query
        if not hits or not (payload.get("links") or {}).get("next"):
            return


def _total(hits_block: dict) -> int:
    total = hits_block.get("total") or 0
    if isinstance(total, dict):
        return int(total.get("value") or 0)
    return int(total)


def _row(project_id: str, hit: dict, query: str) -> dict:
    metadata = hit.get("metadata") or {}
    resource = metadata.get("resource_type") or {}
    if not isinstance(resource, dict):
        resource = {}
    stats = hit.get("stats") or {}
    resource_type = str(resource.get("type") or "")
    subtype = str(resource.get("subtype") or "")
    return {
        "project_id": project_id,
        "source_id": str(hit.get("id")),
        "doi": normalize_doi(metadata.get("doi")),
        "output_type": combined_output_type([resource_type, subtype, str(resource.get("title") or "")]),
        "publication_date": metadata.get("publication_date"),
        "zenodo_views": stats.get("views"),
        "zenodo_downloads": stats.get("downloads"),
        "query": query,
    }


def _pilot_ids() -> list[str]:
    path = INTERIM / "pilot_ids.parquet"
    if not path.exists():
        raise SystemExit("Missing data/interim/pilot_ids.parquet. Run pull_cordis first.")
    return pd.read_parquet(path)["project_id"].astype(str).tolist()


if __name__ == "__main__":
    main()
