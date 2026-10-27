# EU research impact dataset

Pilot dataset of finished Horizon 2020 projects and the outputs linked to them by grant id.

## Scope

- Programme: Horizon 2020.
- Status `CLOSED`, end date in 2018–2022.
- 30 projects, drawn with seed 42 after sorting by grant id.
- Outputs linked on the CORDIS grant agreement number from OpenAIRE, OpenAlex, and Zenodo.
- Citation window: 3 years after the project end date (`config/pilot.yaml`).
- Four Parquet tables in `data/processed/`: `projects`, `organisations`, `outputs`, `project_metrics`.

## Restrictions

- Horizon Europe is out. Citations have not had time to accumulate.
- The sample is not limited to a field. It is a coverage pilot, not the full H2020 corpus. Raise `sample_size` in `config/pilot.yaml` to widen it.
- Impact is several columns on `project_metrics`, not one score. Works typed as reviews are flagged, and the citation metrics are also computed without them.
- `citations_excl_self` counts citations in the 3-year window from works that share no OpenAlex author with the cited work. OpenAlex does not put that count on the work record, so it is pulled from the citing works.
- CORDIS publication rows are kept as a coverage baseline. The output list is filled from OpenAIRE, OpenAlex, and Zenodo, because the CORDIS report is incomplete.
- The CORDIS report dump used here stores image paths, not the publishable summary, so `results_summary` is empty.
- Lifetime citation counts and the windowed counts are both stored. Compare projects on the windowed counts.

| Doc | What it covers |
| --- | --- |
| [docs/setup.md](docs/setup.md) | Commands to build the dataset, and the directory layout |
| [docs/sources.md](docs/sources.md) | Where each source is read from, and what it supplies |
| [docs/processing.md](docs/processing.md) | Pull order, how rows are linked, and how labels are assigned |
| [docs/schema.md](docs/schema.md) | Columns in the four processed tables |
| [docs/viewing.md](docs/viewing.md) | Commands that print the Parquet tables |
| [docs/reuse.md](docs/reuse.md) | Which source data can be published, and the restrictions |
| [docs/data-proposal.md](docs/data-proposal.md) | Why this dataset, where it comes from, and the record shape |
