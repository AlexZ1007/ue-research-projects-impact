# Data proposal: EU research impact

The dataset combines CORDIS, OpenAIRE, OpenAlex, and Zenodo. It connects project funding, consortium information, research outputs, and citation metrics for EU-funded research projects that ended in 2018–2022. Outputs reported by more than one source are merged on the project and the DOI, so publications missing from one source remain in the set. Each project then has comparable indicators, including output counts and citations during and after funding. The citation window is three years after the project end year.

The tables in `data/processed/` are a validation sample of 30 closed projects. All 30 rows of `project_metrics` are in [data-sample.csv](data-sample.csv).

## Sources

Projects come from CORDIS. Outputs are attached by the grant agreement number. URLs and access details are in [sources.md](sources.md).

| Source         | Link                                                                                                                                                 | What is used                                                                 |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| CORDIS         | [cordish2020projects](https://data.europa.eu/data/datasets/cordish2020projects) ([10.2906/112117098108/12](https://doi.org/10.2906/112117098108/12)) | Project metadata, organisations, EuroSciVoc, publications reported to CORDIS |
| OpenAIRE Graph | [research products by grant](https://api.openaire.eu/graph/v3/research-products)                                                                     | Publications, datasets, and software linked to the grant                     |
| OpenAlex       | [works](https://api.openalex.org/works)                                                                                                              | Work type, citation counts, FWCI, citation percentile, open-access flag      |
| Zenodo         | [records](https://zenodo.org/api/records)                                                                                                            | Records that cite the grant, with views and downloads                        |

The validation sample in `data/processed/` has 30 projects, 159 organisation rows, 3,633 output rows, and 30 metric rows. The four Parquet files are about 150 KB. That is the size of the publishable sample.

## Personal data

Published records contain project information, organisation names, countries, publication identifiers, and research metrics. Author names, emails, ORCIDs, addresses, and VAT numbers are excluded. Organisation names come from publicly available project records.

## Schema

Every table joins on `project_id`, the CORDIS grant agreement number, stored as text. The column list is in [schema.md](schema.md).

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

`organisations` — one row per organisation on a grant:

```json
{
  "project_id": "648454",
  "organisation_id": "999986484",
  "name": "UNIVERSITAT AUTONOMA DE BARCELONA",
  "country": "ES",
  "activity_type": "HES",
  "role": "coordinator"
}
```

Activity types are `HES` (university), `REC` (research organisation), `PRC` (private company), `PUB` (public body), and `OTH` (other). Roles are `coordinator`, `participant`, and `thirdParty`.

`outputs` — one row per project–output pair. Rows that share a DOI collapse. Grant DOIs (`10.3030/...`) and funder DOIs (`10.13039/...`) are not treated as output DOIs.

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

## Data licensing and reuse

The published tables are shared under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). They combine records from CORDIS, OpenAIRE, OpenAlex, and Zenodo, and [processing.md](processing.md) describes what was changed. We will credit all four sources and link the licence. OpenAlex and Zenodo do not require attribution for their metadata. We will not present the dataset as endorsed by any of these providers. Source-by-source terms are in [reuse.md](reuse.md).

| Source   | Kept in the tables                                                                                         | Terms                                                                                                                                                                                                                                                                                                      |
| -------- | ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CORDIS   | Project factsheet, organisation legal name, country, and role, EuroSciVoc labels, publication DOI and year | [Commission reuse decision](http://data.europa.eu/eli/dec/2011/833/oj) (2011/833/EU). [CORDIS](https://cordis.europa.eu/about/legal) applies it to EU-owned editorial content as CC BY 4.0. Credit CORDIS and note changes. The notice leaves out third-party works, and patents, trademarks, and logos.   |
| OpenAIRE | DOI, output type, publication date, open-access flag                                                       | [CC BY](https://graph.openaire.eu/docs/apis/terms/). Name OpenAIRE, state changes, link the licence, and make no claim of endorsement.                                                                                                                                                                     |
| OpenAlex | Work id, type, date, citation counts, FWCI, percentile, open-access flag                                   | Metadata is under [CC0](https://openalex.s3.amazonaws.com/LICENSE.txt). Attribution is requested. Abstracts and PDFs are not included. The [website terms](https://openalex.org/OpenAlex_termsofservice.pdf) (revised 2 October 2026) also say that republication of the Data needs prior written consent. |
| Zenodo   | Record id, DOI, type, date, views, downloads                                                               | Metadata is under [CC0](https://about.zenodo.org/policies/), except email addresses, which are excluded. Deposited files keep the depositor's licence and are not included. Use of Zenodo content is limited to non-military purposes.                                                                     |

## How the dataset can be used

Rank the same projects twice: by publications listed in CORDIS, and by citations in the three-year window per million euro, excluding reviews and self-citations. The later evaluation checks whether the order changes.

## Sample

[data-sample.csv](data-sample.csv) is the `project_metrics` table for the validation sample: 30 rows, one per project, with the project acronym added. Empty cells are values the project did not have.
