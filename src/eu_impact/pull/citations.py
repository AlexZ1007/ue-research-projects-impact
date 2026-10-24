"""Count OpenAlex citations that do not share an author with the cited work.

OpenAlex does not store that count on the work. For each work that has an
author id, one grouped request counts citing works with none of those authors.
Works that have a name but no author id are counted by paging the citing works
and dropping a name match. The year counts are stored; the citation window is
applied when the tables are built.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

import pandas as pd

from eu_impact.config import INTERIM, RAW, load_config, mailto
from eu_impact.http import CachedClient
from eu_impact.pull.openalex import fetch

log = logging.getLogger(__name__)

_NAME = re.compile(r"[^a-z0-9]+")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not mailto():
        raise SystemExit("Set OPENALEX_MAILTO in .env before pulling OpenAlex.")
    works_path = INTERIM / "openalex_works.parquet"
    if not works_path.exists():
        raise SystemExit("Missing data/interim/openalex_works.parquet. Run pull.openalex first.")
    config = load_config()
    works = pd.read_parquet(works_path).drop_duplicates("openalex_id")
    authors = _authors_by_work()
    client = CachedClient(pause_seconds=float(config["request_pause_seconds"]))
    base_url = config["openalex"]["base_url"]
    cache_dir = RAW / "openalex" / "citations"
    rows: list[dict] = []
    queried = 0

    for index, work in enumerate(works.itertuples(index=False), start=1):
        people = authors.get(str(work.openalex_id), {"ids": set(), "names": []})
        counts, called = _counts(client, base_url, cache_dir, str(work.openalex_id), work.cited_by_count, people)
        queried += called
        rows.append(
            {
                "openalex_id": work.openalex_id,
                "counts_excl_self": None if counts is None else json.dumps(counts),
            }
        )
        if index % 50 == 0 or index == len(works):
            log.info("citations %s/%s (%s OpenAlex requests)", index, len(works), queried)

    frame = pd.DataFrame(rows)
    INTERIM.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(INTERIM / "openalex_citations.parquet", index=False)
    missing = int(frame["counts_excl_self"].isna().sum())
    log.info("wrote openalex_citations.parquet (%s rows, %s without an author)", len(frame), missing)


def counts_from_groups(groups: list[dict]) -> list[dict]:
    """Turn an OpenAlex publication_year grouping into year counts."""
    rows = []
    for item in groups:
        key = str(item.get("key") or "")
        if not key.isdigit():
            continue
        rows.append({"year": int(key), "cited_by_count": int(item.get("count") or 0)})
    return rows


def shares_name(cited: list[str], citing: list[str]) -> bool:
    """True when two author lists use the same name, ignoring order and punctuation."""
    left = {_name_key(name) for name in cited}
    right = {_name_key(name) for name in citing}
    left.discard(None)
    right.discard(None)
    return bool(left & right)


def nonself_filter(work_id: str, author_ids: list[str]) -> str:
    short = work_id.rsplit("/", 1)[-1]
    parts = [f"cites:{short}"]
    parts.extend(f"authorships.author.id:!{author_id}" for author_id in author_ids)
    return ",".join(parts)


def _counts(client, base_url: str, cache_dir: Path, work_id: str, cited_by_count, people: dict) -> tuple[list[dict] | None, int]:
    if cited_by_count is None or (isinstance(cited_by_count, float) and cited_by_count != cited_by_count):
        cited_by_count = 0
    if int(cited_by_count) <= 0:
        return [], 0
    author_ids = sorted(people["ids"])
    if author_ids:
        payload = _grouped(client, base_url, cache_dir, work_id, author_ids)
        return counts_from_groups(payload.get("group_by") or []), 1
    if people["names"]:
        return _by_name(client, base_url, cache_dir, work_id, people["names"])
    return None, 0


def _grouped(client, base_url: str, cache_dir: Path, work_id: str, author_ids: list[str]) -> dict:
    digest = hashlib.sha1(",".join(author_ids).encode()).hexdigest()[:12]
    short = work_id.rsplit("/", 1)[-1]
    payload = fetch(
        client,
        base_url,
        {"filter": nonself_filter(work_id, author_ids), "group_by": "publication_year", "per_page": 200},
        cache_dir / f"{short}_{digest}.json",
    )
    groups = payload.get("group_by") or []
    groups_count = int((payload.get("meta") or {}).get("groups_count") or len(groups))
    if groups_count > len(groups):
        raise SystemExit(
            f"OpenAlex returned {len(groups)} of {groups_count} citation years for {short}. "
            "The non-self count would be short, so this work was not stored."
        )
    return payload


def _by_name(client, base_url: str, cache_dir: Path, work_id: str, cited_names: list[str]) -> tuple[list[dict], int]:
    short = work_id.rsplit("/", 1)[-1]
    digest = hashlib.sha1("\n".join(sorted(cited_names)).encode()).hexdigest()[:12]
    cursor = "*"
    seen: set[str] = set()
    by_year: dict[int, int] = {}
    calls = 0
    for page in range(500):
        payload = fetch(
            client,
            base_url,
            {
                "filter": f"cites:{short}",
                "select": "id,publication_year,authorships",
                "per_page": 100,
                "cursor": cursor,
            },
            cache_dir / short / f"names_{digest}_{page:03d}.json",
        )
        calls += 1
        batch = payload.get("results") or []
        for citing in batch:
            if shares_name(cited_names, _authorship_names(citing)):
                continue
            year = citing.get("publication_year")
            if year is None:
                continue
            by_year[int(year)] = by_year.get(int(year), 0) + 1
        next_cursor = (payload.get("meta") or {}).get("next_cursor")
        if not batch or not next_cursor or next_cursor in seen:
            break
        seen.add(next_cursor)
        cursor = next_cursor
    counts = [{"year": year, "cited_by_count": by_year[year]} for year in sorted(by_year)]
    return counts, calls


def _authors_by_work() -> dict[str, dict]:
    found: dict[str, dict] = {}
    root = RAW / "openalex"
    if not root.exists():
        return found
    for path in root.rglob("*.json"):
        if path.parent.name == "citations":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("ignoring unreadable cache %s", path)
            continue
        for work in payload.get("results") or []:
            work_id = work.get("id")
            if not work_id:
                continue
            slot = found.setdefault(work_id, {"ids": set(), "names": []})
            for name in _authorship_names(work):
                if name not in slot["names"]:
                    slot["names"].append(name)
            for ship in work.get("authorships") or []:
                author_id = ((ship or {}).get("author") or {}).get("id") or ""
                if author_id:
                    slot["ids"].add(author_id.rsplit("/", 1)[-1])
    return found


def _authorship_names(work: dict) -> list[str]:
    names: list[str] = []
    for ship in work.get("authorships") or []:
        if not isinstance(ship, dict):
            continue
        author = ship.get("author") or {}
        if isinstance(author, dict) and author.get("display_name"):
            names.append(str(author["display_name"]))
        if ship.get("raw_author_name"):
            names.append(str(ship["raw_author_name"]))
    return names


def _name_key(value: str) -> frozenset[str] | None:
    tokens = [token for token in _NAME.sub(" ", value.casefold()).split() if token]
    if not tokens:
        return None
    return frozenset(tokens)


if __name__ == "__main__":
    main()
