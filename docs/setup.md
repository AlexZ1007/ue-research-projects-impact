# Setup

## Commands

```bash
uv sync
cp .env.example .env
uv run python -m eu_impact.pull.cordis
uv run python -m eu_impact.pull.openaire
uv run python -m eu_impact.pull.zenodo
uv run python -m eu_impact.pull.openalex
uv run python -m eu_impact.pull.citations
uv run python -m eu_impact.build.tables
uv run python -m eu_impact.build.coverage
```

Set `OPENALEX_MAILTO` in `.env` before the OpenAlex step.

What each step writes, and how rows are linked, is in [processing.md](processing.md).

## Layout

```
config/pilot.yaml          validation sample size, seed, citation window, source URLs
src/eu_impact/pull/        one script per source, plus the citation pull
src/eu_impact/build/       table build and coverage note
data/processed/            projects, organisations, outputs, project_metrics
```

`config/pilot.yaml` sets the validation sample (currently 30 projects, seed 42). The intended dataset is the wider set of EU-funded research projects that ended in 2018–2022. Its final size is not fixed.
