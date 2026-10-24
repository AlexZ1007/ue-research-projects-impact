"""Download the H2020 dumps and write the 30-project sample."""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from pathlib import Path

import pandas as pd

from eu_impact.config import INTERIM, RAW, load_config
from eu_impact.http import CachedClient
from eu_impact.ids import normalize_doi, normalize_grant_id

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config()
    client = CachedClient(pause_seconds=float(config["request_pause_seconds"]))
    cordis_dir = RAW / "cordis"
    cordis_dir.mkdir(parents=True, exist_ok=True)

    projects_zip = client.download(config["cordis"]["projects_zip"], cordis_dir / "cordis-h2020projects-csv.zip")
    publications_zip = client.download(
        config["cordis"]["publications_zip"],
        cordis_dir / "cordis-h2020projectPublications-csv.zip",
    )
    reports_zip = client.download(config["cordis"]["reports_zip"], cordis_dir / "cordis-h2020reports-csv.zip")
    _note_reports_have_no_text(reports_zip)

    projects = _read_csv(projects_zip, "project.csv")
    organisations = _read_csv(projects_zip, "organization.csv")
    vocabulary = _read_csv(projects_zip, "euroSciVoc.csv")
    publications = _read_csv(
        publications_zip,
        "projectPublications.csv",
        usecols=["id", "doi", "publishedYear", "projectID", "isPublishedAs", "title"],
    )

    projects["project_id"] = projects["id"].map(normalize_grant_id)
    projects = projects.dropna(subset=["project_id"])
    projects["start_date"] = pd.to_datetime(projects["startDate"], errors="coerce")
    projects["end_date"] = pd.to_datetime(projects["endDate"], errors="coerce")
    projects["ec_contribution"] = pd.to_numeric(projects["ecMaxContribution"], errors="coerce")
    projects["total_cost"] = pd.to_numeric(projects["totalCost"], errors="coerce")

    fields = _fields_by_project(vocabulary)
    projects = projects.rename(columns={"topics": "topic_codes"})
    projects = projects.merge(fields, on="project_id", how="left")
    projects["topics"] = projects["topics"].fillna(projects["topic_codes"])
    countries = _coordinator_country(organisations)
    projects = projects.merge(countries, on="project_id", how="left")

    eligible = projects[
        (projects["status"] == config["status"])
        & (projects["end_date"].dt.year >= config["end_year_min"])
        & (projects["end_date"].dt.year <= config["end_year_max"])
    ].sort_values("project_id")
    sample_size = int(config["sample_size"])
    if len(eligible) < sample_size:
        raise SystemExit(f"Only {len(eligible)} projects match the cohort filters, need {sample_size}.")
    sample = (
        eligible.sample(n=sample_size, random_state=int(config["seed"]))
        .sort_values("project_id")
        .reset_index(drop=True)
    )
    ids = set(sample["project_id"])
    log.info("sample of %s from %s closed projects ending %s-%s", sample_size, len(eligible), config["end_year_min"], config["end_year_max"])

    project_rows = pd.DataFrame(
        {
            "project_id": sample["project_id"],
            "acronym": sample["acronym"],
            "title": sample["title"],
            "objective": sample["objective"],
            "programme": sample["frameworkProgramme"],
            "topics": sample["topics"],
            "field": sample["field"],
            "ec_contribution": sample["ec_contribution"],
            "total_cost": sample["total_cost"],
            "start_date": sample["start_date"],
            "end_date": sample["end_date"],
            "coordinator_country": sample["coordinator_country"],
        }
    )
    project_rows["results_summary"] = None

    org_rows = _organisations(organisations, ids)
    publication_rows = _publications(publications, ids)

    INTERIM.mkdir(parents=True, exist_ok=True)
    _write(sample[["project_id"]], INTERIM / "pilot_ids.parquet")
    _write(project_rows, INTERIM / "cordis_projects.parquet")
    _write(org_rows, INTERIM / "cordis_organisations.parquet")
    _write(publication_rows, INTERIM / "cordis_publications.parquet")
    log.info("pilot ids: %s", ", ".join(sample["project_id"].tolist()))


def _read_csv(zip_path: Path, member: str, usecols: list[str] | None = None) -> pd.DataFrame:
    """Read a CORDIS CSV. Fields contain newlines and doubled quotes, which the pandas C parser rejects."""
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text, delimiter=";")
            if usecols is None:
                rows = list(reader)
                columns = list(reader.fieldnames or [])
            else:
                columns = usecols
                rows = [{key: (row.get(key) or "") for key in usecols} for row in reader]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns)


def _note_reports_have_no_text(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open("reportSummaries.csv") as handle:
            header = handle.readline().decode("utf-8-sig", errors="replace")
    if "summary" not in header.lower() and "finalresult" not in header.lower():
        log.info("CORDIS report CSV has no summary text; results_summary will be empty")


def _fields_by_project(vocabulary: pd.DataFrame) -> pd.DataFrame:
    frame = vocabulary.copy()
    frame["project_id"] = frame["projectID"].map(normalize_grant_id)
    frame = frame.dropna(subset=["project_id"])
    frame["title"] = frame["euroSciVocTitle"].str.strip()
    frame["top"] = frame["euroSciVocPath"].map(_top_level)
    rows = []
    for project_id, group in frame.groupby("project_id", sort=False):
        titles = sorted({value for value in group["title"] if value})
        tops = sorted({value for value in group["top"] if value})
        rows.append({"project_id": project_id, "topics": " | ".join(titles), "field": " | ".join(tops)})
    return pd.DataFrame(rows, columns=["project_id", "topics", "field"])


def _top_level(path: str) -> str:
    parts = [part for part in str(path).split("/") if part]
    return parts[0] if parts else ""


def _coordinator_country(organisations: pd.DataFrame) -> pd.DataFrame:
    frame = organisations.copy()
    frame["project_id"] = frame["projectID"].map(normalize_grant_id)
    frame = frame.dropna(subset=["project_id"])
    coordinators = frame[frame["role"].str.lower() == "coordinator"].copy()
    coordinators["order_n"] = pd.to_numeric(coordinators["order"], errors="coerce")
    if coordinators.empty:
        return pd.DataFrame(columns=["project_id", "coordinator_country"])
    coordinators = coordinators.sort_values(["project_id", "order_n"])
    coordinators = coordinators.drop_duplicates("project_id", keep="first")
    return coordinators[["project_id", "country"]].rename(columns={"country": "coordinator_country"})


def _organisations(organisations: pd.DataFrame, ids: set[str]) -> pd.DataFrame:
    frame = organisations.copy()
    frame["project_id"] = frame["projectID"].map(normalize_grant_id)
    frame = frame[frame["project_id"].isin(ids)].copy()
    frame["order_n"] = pd.to_numeric(frame["order"], errors="coerce")
    frame = frame.sort_values(["project_id", "order_n"])
    rows = pd.DataFrame(
        {
            "project_id": frame["project_id"],
            "organisation_id": frame["organisationID"],
            "name": frame["name"],
            "country": frame["country"],
            "activity_type": frame["activityType"],
            "role": frame["role"],
        }
    )
    return rows.drop_duplicates(["project_id", "organisation_id", "role"])


def _publications(publications: pd.DataFrame, ids: set[str]) -> pd.DataFrame:
    frame = publications.copy()
    frame["project_id"] = frame["projectID"].map(normalize_grant_id)
    frame = frame[frame["project_id"].isin(ids)].copy()
    frame["doi"] = frame["doi"].map(normalize_doi)
    year = pd.to_numeric(frame["publishedYear"], errors="coerce")
    return pd.DataFrame(
        {
            "project_id": frame["project_id"].values,
            "doi": frame["doi"].values,
            "published_year": year.values,
            "kind": frame["isPublishedAs"].values,
            "title": frame["title"].values,
            "source_id": frame["id"].values,
        }
    )


def _write(frame: pd.DataFrame, path: Path) -> None:
    frame.to_parquet(path, index=False)
    log.info("wrote %s (%s rows)", path.name, len(frame))


if __name__ == "__main__":
    main()
