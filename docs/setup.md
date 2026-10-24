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
config/pilot.yaml          cohort size, seed, citation window, source URLs
src/eu_impact/pull/        one script per source, plus the citation pull
src/eu_impact/build/       table build and coverage note
data/raw/                  cached downloads
data/interim/              per-source Parquet
data/processed/            projects, organisations, outputs, project_metrics
```
