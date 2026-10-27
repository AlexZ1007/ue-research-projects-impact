# Data proposal: Horizon 2020 project impact

A pilot of 30 closed Horizon 2020 projects that ended in 2018–2022, the outputs linked to each grant, and one row of impact measures per project. The release is four Parquet tables in `data/processed/`: `projects`, `organisations`, `outputs`, and `project_metrics`. A readable extract of 44 real output rows is in [data-sample.csv](data-sample.csv).

The cohort is fixed in `config/pilot.yaml`: status `CLOSED`, end date in 2018–2022, 30 grants drawn with seed 42 after sorting by grant id. The citation window is three years after the project end year.

## Why this dataset

People who compare finished grants need the same three facts on every project: what was funded, what was produced, and how often that work was cited after the grant ended. A programme officer, a bibliometrician, or a student of research policy can use the tables to set a project’s output and citation record next to its EU contribution, its field, and the size of its consortium. Lifetime citation counts mix projects that ended in different years. The windowed counts do not.

Each source already publishes part of this.

| Source | What a user already gets | What this pilot adds on top |
| --- | --- | --- |
| [CORDIS](https://data.europa.eu/data/datasets/cordish2020projects) | Factsheet, consortium, EuroSciVoc, a publication list | Citation counts, a fixed window, outputs the CORDIS list misses |
| [OpenAIRE Graph](https://graph.openaire.eu/) | Products linked to the grant id, including after the project ends | Field-weighted citations, a percentile, project budget rates |
| [OpenAlex](https://openalex.org/) | Citations, FWCI, percentile, open-access flag | The grant cohort, the consortium, and works found by DOI when the award link is missing |
| [Zenodo](https://zenodo.org/) | Records that cite the grant, with views and downloads | A place in the project row, next to the publications |

In this pilot, 66.5% of OpenAIRE outputs that have a DOI (1,016 of 1,527) are absent from the CORDIS publication list for the same grant. CORDIS is the right list of projects and the right baseline. It is the wrong place to stop: the publication report is incomplete, this dump’s report summaries are image paths, and the factsheet has no citation metrics. OpenAlex does not carry the EU contribution or the consortium. Zenodo does not define a project cohort. The pilot is the join of the four on the CORDIS grant agreement number, with DOI duplicates collapsed, a type label, a before/during/after label, and project-level rates per million euro.

The Horizon Dashboard and the four source databases remain the place for the full programme. This release is the 30-grant coverage pilot.

## Sources

We read CORDIS from the monthly bulk zips and the other three sources from their APIs, one grant at a time. Details of each URL are in [sources.md](sources.md). What may be republished is in [reuse.md](reuse.md).

| Source | Link | Licence | Approximate size |
| --- | --- | --- | --- |
| CORDIS H2020 projects | [cordish2020projects](https://data.europa.eu/data/datasets/cordish2020projects) ([10.2906/112117098108/12](https://doi.org/10.2906/112117098108/12)) | [Commission reuse decision](http://data.europa.eu/eli/dec/2011/833/oj), applied by [CORDIS](https://cordis.europa.eu/about/legal) as CC BY 4.0 for EU-owned editorial content. Credit CORDIS and note changes | Full-programme zips: projects ~53 MB, publications ~64 MB, report metadata ~3.5 MB |
| OpenAIRE Graph | [`research-products?relProjectCode=`](https://api.openaire.eu/graph/v3/research-products) | [CC BY](https://graph.openaire.eu/docs/apis/terms/). Credit OpenAIRE | API pages for these 30 grants. The Graph bulk dump is a separate, much larger download and is not used |
| OpenAlex | [`/works`](https://api.openalex.org/works), by DOI and by award id | Metadata under [CC0](https://openalex.s3.amazonaws.com/LICENSE.txt). Abstracts and PDFs are outside that waiver and are not stored | API pages for the matched works. The public snapshot is not downloaded |
| Zenodo | [`/api/records?q=grants.code:`](https://zenodo.org/api/records) | Metadata under [CC0](https://about.zenodo.org/policies/), except email addresses, which we drop. Deposited files keep the depositor’s licence and are not downloaded. Use is limited to non-military purposes | API pages for these 30 grants |

The published pilot is 30 projects, 159 organisation rows, 3,633 output rows, and 30 metric rows. The four Parquet files are about 150 KB. The unpublished API and zip cache is about 158 MB and stays on disk only.

## Sensitive data

The published tables contain project text, organisation legal names, countries, output identifiers, and counts. They do not contain author names, ORCIDs, email addresses, street addresses, or VAT numbers. Those fields are present in the raw CORDIS, OpenAIRE, OpenAlex, and Zenodo responses. `data/raw/` is gitignored, and those files are not pushed. Author names are read only while dropping self-citations, and they are not a column on `outputs`. Organisation names in the release are the public legal names from the CORDIS factsheet.

`results_summary` is empty. The report dump stores image paths, and those paths are left in the cache.

## Schema

Every table joins on `project_id`, the CORDIS grant agreement number, stored as text. The column list is in [schema.md](schema.md). Three records from grant 648454 (SPIN-PORICS) show the shape. Floats in the metric row are rounded; the Parquet values are unrounded. The objective in the table is the full CORDIS text.

`projects` — one row per grant:

```json
{
  "project_id": "648454",
  "acronym": "SPIN-PORICS",
  "title": "Merging Nanoporous Materials with Energy-Efficient Spintronics",
  "objective": "This Project aims to integrate engineered nanoporous materials into novel energy-efficient spintronic applications. [...]",
  "programme": "H2020",
  "topics": "electric energy | nano-materials | nanocomposites | semiconductivity | spintronics",
  "field": "engineering and technology | natural sciences",
  "ec_contribution": 1794380,
  "total_cost": 1794380,
  "start_date": "2015-09-01",
  "end_date": "2020-12-31",
  "coordinator_country": "ES",
  "results_summary": null
}
```

`organisations` — one row per organisation on a grant. The coordinator of the same project is `organisation_id` 999986484, UNIVERSITAT AUTONOMA DE BARCELONA, country `ES`, `activity_type` `HES`, `role` `coordinator`. Other roles are `participant` and `thirdParty`. Activity types are `HES`, `REC`, `PRC`, `PUB`, and `OTH`.

`outputs` — one row per project–output pair. Rows that share a DOI collapse. Grant DOIs (`10.3030/...`) and funder DOIs (`10.13039/...`) are dropped.

```json
{
  "project_id": "648454",
  "doi": "10.1063/5.0079762",
  "openalex_id": "https://openalex.org/W4213098202",
  "output_type": "article",
  "publication_date": "2022-02-14",
  "timing": "after",
  "cited_by_count": 35,
  "citations_in_window": 11,
  "citations_excl_self": 8,
  "fwci": 2.7304,
  "citation_percentile": 0.923,
  "is_oa": true,
  "is_review": false,
  "zenodo_views": null,
  "zenodo_downloads": null,
  "sources": "openaire|openalex"
}
```

`output_type` is `article`, `review`, `dataset`, `software`, or `other`. `timing` is `before`, `during`, or `after` the project dates. `sources` lists which of `cordis`, `openaire`, `openalex`, and `zenodo` asserted the link. FWCI is copied from OpenAlex: `1.0` is the expected citation rate for works of the same type, field, and year.

`project_metrics` — one row per grant, summed from the labelled outputs:

```json
{
  "project_id": "648454",
  "n_outputs": 89,
  "n_articles": 80,
  "n_reviews": 0,
  "n_datasets": 0,
  "n_software": 0,
  "mean_fwci": 1.515,
  "mean_fwci_excl_reviews": 1.515,
  "pct_top10": 0.127,
  "pct_top10_excl_reviews": 0.127,
  "n_countries": 1,
  "n_organisations": 1,
  "zenodo_views": 618,
  "zenodo_downloads": 700,
  "n_outputs_per_million_eur": 49.6,
  "citations_in_window": 1343,
  "citations_in_window_per_million_eur": 748.4,
  "pct_oa": 0.987,
  "n_outputs_during": 76,
  "n_outputs_after": 11,
  "n_outputs_before": 0,
  "citations_excl_self": 890
}
```

## How we will show the set is useful

Rank the same 30 grants twice: once by how many publications CORDIS lists, and once by citations in the three-year window per million euro, with reviews removed and self-citations removed. The coverage figures already say the two lists are different sets of works. A change in order would show that the join changes a comparison a reader would actually make. That check belongs to the later evaluation.

## Sample

[data-sample.csv](data-sample.csv) has 44 rows from `data/processed/outputs.parquet`, with the project acronym added. Eleven grants are represented: 24 articles, 6 datasets, 4 reviews, all 4 software rows in the pilot, and 6 CORDIS-only rows that have no DOI and no citation count. Empty cells are values the sources did not provide. The raw downloads are not in the repository.
