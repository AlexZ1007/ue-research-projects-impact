# Sources

Projects come from CORDIS. Outputs are attached by the grant agreement number, the id in `https://cordis.europa.eu/project/id/{id}`. The dataset covers EU-funded research projects that ended in 2018–2022. The current build reads a validation sample, not the full set of such projects.

| Source | What it supplies | How it is read |
| --- | --- | --- |
| CORDIS | Project metadata, organisations, EuroSciVoc field, publications reported to CORDIS | Monthly bulk CSV zips from [cordish2020projects](https://data.europa.eu/data/datasets/cordish2020projects?locale=en): `cordis-h2020projects-csv.zip`, `cordis-h2020projectPublications-csv.zip`, `cordis-h2020reports-csv.zip` |
| OpenAIRE Graph | Publications, datasets, and software linked to the grant, including items published after the project ends | `GET https://api.openaire.eu/graph/v3/research-products?relProjectCode={grantId}` with cursor paging |
| OpenAlex | Work type, citation count, FWCI, citation percentile, open-access flag, citations by year | By DOI, then by `awards.funder_award_id` for works the other sources missed |
| Zenodo | Records that cite the EU grant, with views and downloads | `GET https://zenodo.org/api/records?q=grants.code:{grantId}` |

`metadata.grants.code` and `grants.internal_id:10.13039/501100000780::{grantId}` are tried when `grants.code` returns nothing. The query that returned rows is stored on each Zenodo hit.

The October 2026 report-summaries CSV has an `attachment` column of image paths. It does not contain the summary text, so `results_summary` is left empty.

What may be published from these sources is in [reuse.md](reuse.md).

OpenAlex requests without `OPENALEX_API_KEY` share a small daily budget with other users on the same network. `OPENALEX_MAILTO` is still sent. Set the key in `.env` if a pull is rejected for budget.

`citations_excl_self` is not on the work record. For each cited work that has an OpenAlex author id, a grouped request counts citing works that have none of those authors, by publication year. The citation window is applied later, in the same way as `citations_in_window`. A work with a name but no author id is handled by reading the citing works and dropping a name match. Author names are not stored on `outputs`.
