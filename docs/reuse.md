# Reuse

The four tables in `data/processed/` can be published. The cached downloads in `data/raw/` cannot. `data/interim/` is a working copy, and it is not the release.

The tables are a 30-project extract, relabelled and aggregated. They are a sample, not a copy of any source database. Share them under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): name CORDIS and OpenAIRE, link this licence, point to [processing.md](processing.md) for what was changed, and do not present the result as endorsed by any provider. OpenAlex and Zenodo metadata do not require attribution. Name them as well.

This note records the terms those providers publish. It is not a legal opinion.

| Source | Kept in the processed tables | Publication |
| --- | --- | --- |
| CORDIS | Project factsheet, organisation legal name, country, and role, EuroSciVoc labels, publication DOI and year | Allowed under the Commission reuse notice, with credit |
| OpenAIRE | DOI, output type, publication date, open-access flag | Allowed under CC BY, with credit |
| OpenAlex | Work id, type, date, citation counts, FWCI, percentile, open-access flag | Metadata is CC0. Abstracts and PDFs are outside that waiver |
| Zenodo | Record id, DOI, type, date, views, downloads | Metadata is CC0. Each file keeps the depositor's licence |

## CORDIS

The three zips are distributions of the [Horizon 2020 projects dataset](https://data.europa.eu/data/datasets/cordish2020projects) ([10.2906/112117098108/12](https://doi.org/10.2906/112117098108/12)). data.europa.eu licenses every distribution under the [European Commission reuse notice](http://data.europa.eu/eli/dec/2011/833/oj) (Decision 2011/833/EU).

The [CORDIS copyright notice](https://cordis.europa.eu/about/legal) applies that decision to editorial content owned by the EU as CC BY 4.0. Reuse needs credit and a note of changes. The notice leaves out third-party works, and patents, trademarks, and logos. Materials supplied by grant beneficiaries follow the terms of that grant.

`projects` and `organisations` use the public factsheet: acronym, title, objective, programme, dates, budget, EuroSciVoc, and the organisation's legal name, country, activity type, and role.

The same zips contain columns the tables do not copy. Leave these in the cache: author names on publication rows, street, postcode, and VAT number on organisation rows, and the report-summary attachment paths. The report CSV has no summary text, so `results_summary` is empty. Deliverable files, the patent subset, and the ERC principal-investigator list are not downloaded. Publication titles stay in `data/interim/cordis_publications.parquet` only. The publications distribution is under the same reuse notice.

## OpenAIRE

The [Graph API terms](https://graph.openaire.eu/docs/apis/terms/) release the returned records under CC BY, for commercial and non-commercial reuse, provided OpenAIRE is named as the source. The [Graph FAQ](https://graph.openaire.eu/faq) states the rest of the CC BY duties: credit, state changes, link the licence, and make no claim of endorsement. Bulk dumps on Zenodo use [CC BY 4.0](https://graph.openaire.eu/docs/bulk-access/).

The tables keep the DOI, a normalised type, the publication date, and the open-access flag. Cached pages also hold titles, descriptions, authors, and contact fields. Those pages stay in `data/raw/`.

Unauthenticated calls are limited to 60 an hour. That limit is on access.

## OpenAlex

The public snapshot carries a [CC0 1.0 waiver](https://openalex.s3.amazonaws.com/LICENSE.txt). OpenAlex's guide says the metadata is CC0, with no personal-use limit and no need to ask permission ([how the dataset is shared](https://help.openalex.org/data/how-its-built/), [snapshot and API pricing](https://help.openalex.org/access/sync/)). Attribution is requested.

The [website terms](https://openalex.org/OpenAlex_termsofservice.pdf), revised 2 October 2026, also say that republication of the Data needs prior written consent. That sentence conflicts with the CC0 waiver. The citation counts, FWCI, percentile, type, date, and open-access flag kept here are metadata covered by the waiver. Abstracts and PDFs sit outside it, and they are not stored. CC0 does not clear rights OpenAlex does not hold.

Author names are read only to drop self-citations. They are not a column on `outputs`.

An API key and the daily request budget govern access to the hosted API. They leave the metadata licence unchanged.

## Zenodo

The [terms of use](https://about.zenodo.org/terms/) (v1.3) and the [policies](https://about.zenodo.org/policies/) waive rights in the metadata under CC0, except email addresses. Files remain under the licence the depositor chose. Use of Zenodo content is limited to non-military purposes.

The tables store the record id, DOI, type, date, and the public view and download counts. Titles, descriptions, creator names, emails, and files stay out of the tables. The cached record JSON includes them, and the depositor's licence, so the cache stays unpublished.

## Leave unpublished

- `data/raw/`: the CORDIS zips and the API pages.
- `data/interim/`: it still carries CORDIS publication titles.
- Report-summary images, deliverable files, and any Zenodo or publisher file.
- Abstracts and full texts.
- Author names, ORCIDs, street addresses, VAT numbers, and email addresses.
