# EU research impact dataset

The dataset combines CORDIS, OpenAIRE, OpenAlex, and Zenodo for EU-funded research projects that ended in 2018–2022. It connects project funding and consortium information with research outputs and citation metrics. Outputs found in more than one source are merged, so a publication missing from one source can still be included. Each project has comparable indicators, including citations during and after funding.

The tables in `data/processed/` are a validation sample of 30 projects, drawn with seed 42 after sorting by grant id. The sample is for testing. It is not the intended size of the dataset. The final number of projects is not fixed.

## Scope

- EU-funded research projects with status `CLOSED` and an end date in 2018–2022.
- Outputs linked on the CORDIS grant agreement number.
- Citation window: 3 years after the project end year (`config/pilot.yaml`).
- Four Parquet tables: `projects`, `organisations`, `outputs`, `project_metrics`.

The validation sample is drawn from the CORDIS Horizon 2020 project distribution and is not limited to one field. On this sample, 66.5% of OpenAIRE outputs with a DOI (1,016 of 1,527) are absent from the CORDIS publication list for the same project. Counts are in [data/processed/coverage.md](data/processed/coverage.md).

## Measures

- Impact is several columns on `project_metrics`. Works typed as reviews are flagged, and the citation metrics are also computed without them.
- `citations_excl_self` counts citations in the 3-year window from works that share no OpenAlex author with the cited work.
- Lifetime citation counts and the windowed counts are both stored. Compare projects on the windowed counts.
- `results_summary` is empty. The CORDIS report file used here has image paths, not the summary text.

## Documentation

| Doc | What it covers |
| --- | --- |
| [docs/setup.md](docs/setup.md) | Commands to build the dataset, and the directory layout |
| [docs/sources.md](docs/sources.md) | Where each source is read from, and what it supplies |
| [docs/processing.md](docs/processing.md) | Pull order, how rows are linked, and how labels are assigned |
| [docs/schema.md](docs/schema.md) | Columns in the four processed tables |
| [docs/viewing.md](docs/viewing.md) | Commands that print the Parquet tables |
| [docs/reuse.md](docs/reuse.md) | Source licences, attribution, and what is left out of the tables |
| [docs/data-proposal.md](docs/data-proposal.md) | Dataset description, licensing summary, schema, and a data sample |
