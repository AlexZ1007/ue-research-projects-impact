"""Pull OpenAIRE research products for the pilot grant ids."""

from __future__ import annotations

import logging

import pandas as pd

from eu_impact.classify import combined_output_type
from eu_impact.config import INTERIM, RAW, load_config
from eu_impact.http import CachedClient
from eu_impact.ids import extract_dois

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config()
    ids = _pilot_ids()
    client = CachedClient(pause_seconds=float(config["request_pause_seconds"]))
    base_url = config["openaire"]["base_url"]
    page_size = int(config["openaire"]["page_size"])
    logged_keys = False
    rows: list[dict] = []
    projects_with_hits = 0

    for index, project_id in enumerate(ids, start=1):
        records, logged_keys = _pages(
            client, base_url, project_id, page_size, logged_keys
        )
        if records:
            projects_with_hits += 1
        log.info("OpenAIRE %s/%s %s -> %s products", index, len(ids), project_id, len(records))
        for record in records:
            rows.append(_row(project_id, record))

    if projects_with_hits == 0:
        raise SystemExit(
            "OpenAIRE returned no research products for any pilot project. "
            "Check relProjectCode against the Graph API docs before continuing."
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        frame = pd.DataFrame(columns=["project_id", "source_id", "doi", "output_type", "publication_date", "is_oa"])
    INTERIM.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(INTERIM / "openaire_outputs.parquet", index=False)
    log.info("wrote openaire_outputs.parquet (%s rows)", len(frame))


def _pages(client: CachedClient, base_url: str, project_id: str, page_size: int, logged_keys: bool) -> tuple[list[dict], bool]:
    cursor = "*"
    seen: set[str] = set()
    records: list[dict] = []
    for page in range(500):
        cache = RAW / "openaire" / project_id / f"page_{page:03d}.json"
        payload = client.get_json(
            base_url,
            {"relProjectCode": project_id, "pageSize": page_size, "cursor": cursor},
            cache,
        )
        batch = payload.get("results") or []
        header = payload.get("header") or {}
        if batch and not logged_keys:
            log.info("OpenAIRE result keys: %s", ", ".join(sorted(batch[0].keys())))
            logged_keys = True
        records.extend(batch)
        next_cursor = header.get("nextCursor")
        if not batch or not next_cursor or next_cursor in seen:
            break
        seen.add(next_cursor)
        cursor = next_cursor
    return records, logged_keys


def _row(project_id: str, record: dict) -> dict:
    instance_types = [
        str(instance.get("type") or "")
        for instance in (record.get("instances") or [])
        if isinstance(instance, dict)
    ]
    return {
        "project_id": project_id,
        "source_id": record.get("id"),
        "doi": _doi(record),
        "output_type": combined_output_type(
            [str(record.get("type") or ""), *instance_types]
        ),
        "publication_date": _publication_date(record),
        "is_oa": _is_oa(record),
    }


def _doi(record: dict) -> str | None:
    blobs: list[object] = []
    for pid in record.get("pids") or []:
        if isinstance(pid, dict):
            blobs.append(pid.get("value"))
    for instance in record.get("instances") or []:
        if not isinstance(instance, dict):
            continue
        for alt in instance.get("alternateIdentifiers") or []:
            if isinstance(alt, dict):
                blobs.append(alt.get("value"))
        blobs.extend(instance.get("urls") or [])
    for blob in blobs:
        found = extract_dois(blob)
        if found:
            return found[0]
    return None


def _publication_date(record: dict) -> str | None:
    if record.get("publicationDate"):
        return str(record["publicationDate"])[:10]
    for instance in record.get("instances") or []:
        if isinstance(instance, dict) and instance.get("publicationDate"):
            return str(instance["publicationDate"])[:10]
    return None


def _is_oa(record: dict) -> bool | None:
    rights: list[dict] = []
    best = record.get("bestAccessRight")
    if isinstance(best, dict):
        rights.append(best)
    for instance in record.get("instances") or []:
        if not isinstance(instance, dict):
            continue
        access = instance.get("accessRight")
        if isinstance(access, dict):
            rights.append(access)
    if not rights:
        return None
    for access in rights:
        label = str(access.get("label") or "").strip().upper()
        code = str(access.get("code") or "")
        if label == "OPEN" or code == "c_abf2":
            return True
    return False


def _pilot_ids() -> list[str]:
    path = INTERIM / "pilot_ids.parquet"
    if not path.exists():
        raise SystemExit("Missing data/interim/pilot_ids.parquet. Run pull_cordis first.")
    frame = pd.read_parquet(path)
    return frame["project_id"].astype(str).tolist()


if __name__ == "__main__":
    main()
