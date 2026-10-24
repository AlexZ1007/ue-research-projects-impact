# Schema

All four tables are Parquet in `data/processed/`. Join key is `project_id`, the CORDIS grant agreement number, stored as text. Every row has `retrieved_at`, the time the tables were built.

## projects

| column | description |
| --- | --- |
| project_id | CORDIS grant agreement number |
| acronym | Project acronym |
| title | Project title |
| objective | Project objective text |
| programme | Framework programme (`H2020`) |
| topics | EuroSciVoc titles, joined with ` \| ` |
| field | Distinct top-level EuroSciVoc domains, joined with ` \| ` |
| ec_contribution | EU contribution, from CORDIS `ecMaxContribution`, in euro |
| total_cost | Total project cost, in euro |
| start_date | Project start date |
| end_date | Project end date |
| coordinator_country | Country code of the coordinating organisation |
| results_summary | Empty. The report dump has image paths, not the summary text. See [sources.md](sources.md) |
| retrieved_at | Time this table was built |

## organisations

One row per organisation on a pilot project.

| column | description |
| --- | --- |
| project_id | Grant this organisation belongs to |
| organisation_id | CORDIS organisation id |
| name | Organisation name |
| country | Country code of the organisation's legal seat. `EL` is Greece |
| activity_type | `HES` university, `REC` research organisation, `PRC` private company, `PUB` public body, `OTH` other |
| role | `coordinator` leads the project, `participant` is a consortium member, `thirdParty` is linked but not a full member |
| retrieved_at | Time this table was built |

## outputs

One row per project–output pair. Rows with a DOI collapse to `(project_id, doi)`. Rows without a DOI stay separate per source id. Grant DOIs (`10.3030/...`) and funder DOIs (`10.13039/...`) are not treated as output DOIs.

| column | description |
| --- | --- |
| project_id | Grant this output is linked to |
| doi | Output DOI, lowercase, without the resolver prefix |
| openalex_id | OpenAlex work id, when the DOI or the award id matched |
| output_type | (label) `article`, `review`, `dataset`, `software`, or `other`. Mapped here from the OpenAlex work type, or else the OpenAIRE, Zenodo, or CORDIS type string |
| publication_date | Publication date. A CORDIS row with only `publishedYear` is stored as 1 January of that year and classed by year |
| timing | (label) `before`, `during`, or `after` the project. Empty when a date is missing |
| cited_by_count | Lifetime citations from OpenAlex |
| citations_in_window | OpenAlex citations in years up to `end year + citation_window_years`. Empty when year counts are missing. Lifetime counts are not used as a substitute |
| citations_excl_self | Same window, excluding citing works that share an OpenAlex author id with this work. A work with no author id is matched on author name instead (`Last, First` and `First Last` are the same name). Empty when the work is not in OpenAlex, or it has no author id and no author name |
| fwci | \* Field-weighted citation impact, copied from OpenAlex |
| citation_percentile | OpenAlex percentile on a 0–1 scale |
| is_oa | (label) Open access. True if any source says so |
| is_review | (label) True when `output_type` is `review` |
| zenodo_views | Zenodo views |
| zenodo_downloads | Zenodo downloads |
| sources | (label) Which of `cordis`, `openaire`, `openalex`, and `zenodo` asserted the link, joined with `\|` |
| retrieved_at | Time this table was built |

## project_metrics

One row per project, computed from `organisations` and `outputs`. A mean or a share is empty when nothing in that project has the underlying value.

| column | description |
| --- | --- |
| project_id | Grant these metrics belong to |
| n_outputs | Output rows |
| n_articles | Outputs typed `article` |
| n_reviews | Outputs typed `review` |
| n_datasets | Outputs typed `dataset` |
| n_software | Outputs typed `software` |
| mean_fwci | \* Mean of `fwci` over outputs that have one |
| mean_fwci_excl_reviews | \* Same mean, reviews left out |
| pct_top10 | Share of outputs with a percentile that are in the top 10% |
| pct_top10_excl_reviews | Same share, reviews left out |
| n_countries | Distinct organisation countries |
| n_organisations | Distinct organisations |
| zenodo_views | Sum of Zenodo views |
| zenodo_downloads | Sum of Zenodo downloads |
| n_outputs_per_million_eur | Output count per million euro of `ec_contribution` |
| citations_in_window | Sum of `citations_in_window` |
| citations_in_window_per_million_eur | That sum per million euro of `ec_contribution` |
| pct_oa | Share of articles and reviews with `is_oa` |
| n_outputs_during | Outputs published during the project |
| n_outputs_after | Outputs published after the project end |
| n_outputs_before | Outputs published before the project start |
| citations_excl_self | Sum of `citations_excl_self`. Empty output values are skipped |
| retrieved_at | Time this table was built |

\* FWCI divides a paper's citations by the number expected for works of the same type, field, and publication year. `1.0` is that average. `2.0` is about twice as often, `0.5` about half. This project stores the OpenAlex value and does not recompute it.

Top 10% in `project_metrics` uses OpenAlex `is_in_top_10_percent`, or `citation_percentile >= 0.9` when that flag is absent.
