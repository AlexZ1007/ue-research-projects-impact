# Processing

Each step reads `config/pilot.yaml` and writes Parquet. Raw API and zip responses stay in `data/raw/` and are reused on the next run. Interim tables are `data/interim/`. The four final tables are `data/processed/`. Column definitions are in [schema.md](schema.md). Source URLs are in [sources.md](sources.md).

Run the steps in this order. Later pulls use `data/interim/pilot_ids.parquet` from CORDIS. OpenAlex also needs the DOI lists from the earlier pulls.

```bash
uv run python -m eu_impact.pull.cordis
uv run python -m eu_impact.pull.openaire
uv run python -m eu_impact.pull.zenodo
uv run python -m eu_impact.pull.openalex
uv run python -m eu_impact.pull.citations
uv run python -m eu_impact.build.tables
uv run python -m eu_impact.build.coverage
```

Set `OPENALEX_MAILTO` in `.env` before the OpenAlex step.

## Pull

| Step | Writes | What it keeps |
| --- | --- | --- |
| `pull.cordis` | `pilot_ids`, `cordis_projects`, `cordis_organisations`, `cordis_publications` | Closed H2020 projects with an end date in 2018–2022. After sorting by grant id, `sample_size` projects are drawn with `seed`. |
| `pull.openaire` | `openaire_outputs` | Research products linked to the grant id |
| `pull.zenodo` | `zenodo_outputs` | Records that cite the grant, with views and downloads |
| `pull.openalex` | `openalex_works` | Works for the grant award id, then any known DOI that search missed |
| `pull.citations` | `openalex_citations` | Citing works that share no author with the cited work, counted by publication year |

`results_summary` is empty. The CORDIS report dump has image paths, not the summary text.

## Linking

`build.tables` stacks the four output lists and collapses rows that share a `(project_id, doi)`. A row with no DOI stays separate, keyed by source and source id. Grant DOIs (`10.3030/...`) and funder DOIs (`10.13039/...`) are dropped.

Where the sources disagree:

- The publication date prefers a full day over a year-only CORDIS date, and prefers the OpenAlex day when several sources have one.
- Citation fields, FWCI, and the percentile come from the OpenAlex row.
- `is_oa` is true when any source says so. Zenodo rows are stored as open access. It is empty when no source has a flag.
- Zenodo views and downloads keep the largest number reported.
- `sources` is the sorted list of sources that asserted the link, joined with `|`.

## Labelling

Labels are assigned in `build.tables`. They are not copied from a single source string.

### `output_type`

Each source string is first collapsed to `article`, `review`, `dataset`, `software`, or `other`.

| Source string | Label |
| --- | --- |
| `review`, `review-article`, `review article`, `literature review`, or OpenAlex type `review` | `review` |
| `dataset`, or OpenAlex type `dataset` | `dataset` |
| A string containing `software`, or OpenAlex type `software` | `software` |
| `publication`, `article`, `peer reviewed articles`, a string containing `article`, or OpenAlex type `article` | `article` |
| Any other non-empty type | `other` |

On a merged row, `review` wins if any source said so. Otherwise the OpenAlex label is kept when it is not `other`. Otherwise the first match in order is `dataset`, `software`, `article`. `is_review` is true when the merged type is `review`.

### `timing`

Compared with the project start and end dates.

| Case | Label |
| --- | --- |
| Published before the start | `before` |
| Published from the start through the end | `during` |
| Published after the end | `after` |
| Date or project bound missing | empty |

A CORDIS row that only has `publishedYear` is stored as 1 January of that year and compared by calendar year, so that placeholder day is not treated as a real date.

### `field`

EuroSciVoc paths from CORDIS. `topics` is the distinct titles, joined with ` | `. `field` is the distinct top-level path segments, joined the same way. Organisation `activity_type` and `role` are kept as CORDIS sent them.

### Citation window

`citation_window_years` in `config/pilot.yaml` is 3. The horizon is the project end year plus that many years.

`citations_in_window` sums OpenAlex `counts_by_year` for years up to the horizon. It is empty when those year counts are missing. Lifetime `cited_by_count` is not used as a substitute.

`citations_excl_self` sums the year counts from `pull.citations` through the same horizon. A self-citation is a citing work that shares an OpenAlex author id with the cited work. A cited work with no author id is matched on author name instead (`Last, First` and `First Last` are the same name). The count is empty when the work has no author id and no author name. An empty citing list is zero.

Top 10% uses the OpenAlex flag `is_in_top_10_percent` when present, otherwise `citation_percentile >= 0.9`. That flag is not a column on `outputs`. It is only used for `pct_top10` and `pct_top10_excl_reviews`.

## Project metrics

`project_metrics` is one row per project, summed from the labelled outputs and the organisations.

- Output counts follow `output_type`. Timing counts follow `timing`.
- `mean_fwci_excl_reviews` and `pct_top10_excl_reviews` drop rows with `is_review`.
- `pct_oa` is the share of articles and reviews with `is_oa`.
- A mean or a share is empty when no row in the project has the underlying value. A sum skips empty values.
- Per-million-euro rates divide by `ec_contribution`. They are empty when the contribution is missing or not positive.

`build.coverage` then writes `data/processed/coverage.md` from the finished tables.
