"""Write the pilot coverage note."""

from __future__ import annotations

import logging

import pandas as pd

from eu_impact.config import INTERIM, PROCESSED

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    projects = pd.read_parquet(PROCESSED / "projects.parquet")
    outputs = pd.read_parquet(PROCESSED / "outputs.parquet")
    cordis = pd.read_parquet(INTERIM / "cordis_publications.parquet")
    text = render(projects, outputs, cordis)
    path = PROCESSED / "coverage.md"
    path.write_text(text, encoding="utf-8")
    log.info("wrote %s", path)
    print(text)


def render(projects: pd.DataFrame, outputs: pd.DataFrame, cordis: pd.DataFrame) -> str:
    n_projects = len(projects)
    lines = ["# Pilot coverage", ""]
    lines.append(f"{n_projects} projects. {len(outputs)} output rows after linking on grant id and DOI.")
    lines.append("")
    lines.append("Share of projects with at least one output from each source:")
    lines.append("")
    for source in ("cordis", "openaire", "openalex", "zenodo"):
        count = _projects_with(outputs, source)
        lines.append(f"- {source}: {_pct(count, n_projects)} ({count}/{n_projects})")
    lines.append("")

    with_doi = outputs[outputs["doi"].notna() & (outputs["doi"].astype(str) != "")] if not outputs.empty else outputs
    lines.append(
        f"Outputs with a DOI: {_pct(len(with_doi), len(outputs))} ({len(with_doi)}/{len(outputs)})."
    )
    found = with_doi[with_doi["openalex_id"].notna()] if not with_doi.empty else with_doi
    lines.append(
        f"Those DOIs found in OpenAlex: {_pct(len(found), len(with_doi))} ({len(found)}/{len(with_doi)})."
    )
    with_fwci = found[pd.to_numeric(found["fwci"], errors="coerce").notna()] if not found.empty else found
    lines.append(
        f"OpenAlex works with FWCI: {_pct(len(with_fwci), len(found))} ({len(with_fwci)}/{len(found)})."
    )
    lines.append("")

    openaire = _with_source(outputs, "openaire")
    listed = _cordis_doi_pairs(cordis)
    not_listed = 0
    for record in openaire.itertuples(index=False):
        doi = record.doi if not pd.isna(record.doi) else None
        if not doi or (str(record.project_id), str(doi)) not in listed:
            not_listed += 1
    lines.append(
        "OpenAIRE outputs that the CORDIS publication list does not contain, "
        f"matched on DOI within the project: {_pct(not_listed, len(openaire))} "
        f"({not_listed}/{len(openaire)})."
    )

    timed = outputs[outputs["timing"].notna()] if not outputs.empty else outputs
    after = timed[timed["timing"] == "after"] if not timed.empty else timed
    lines.append(
        f"Outputs with a known timing that were published after the project end: "
        f"{_pct(len(after), len(timed))} ({len(after)}/{len(timed)})."
    )
    lines.append("")
    return "\n".join(lines)


def _with_source(outputs: pd.DataFrame, source: str) -> pd.DataFrame:
    if outputs.empty:
        return outputs
    return outputs[outputs["sources"].fillna("").str.contains(source, regex=False)]


def _projects_with(outputs: pd.DataFrame, source: str) -> int:
    matched = _with_source(outputs, source)
    if matched.empty:
        return 0
    return int(matched["project_id"].nunique())


def _cordis_doi_pairs(cordis: pd.DataFrame) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    if cordis.empty:
        return pairs
    for record in cordis.itertuples(index=False):
        if pd.isna(record.doi) or not record.doi:
            continue
        pairs.add((str(record.project_id), str(record.doi)))
    return pairs


def _pct(part: int, whole: int) -> str:
    if whole == 0:
        return "n/a"
    return f"{100 * part / whole:.1f}%"


if __name__ == "__main__":
    main()
