# Viewing the tables

The tables are Parquet. These commands print them in the terminal. `uv sync` installs the `duckdb` command used here. `objective` is long, so the projects query lists columns instead of `SELECT *`.

```bash
uv run duckdb -c "SELECT project_id, acronym, title, field, ec_contribution, total_cost, start_date, end_date, coordinator_country FROM 'data/processed/projects.parquet' LIMIT 30"
```

```bash
uv run duckdb -c "SELECT * FROM 'data/processed/organisations.parquet' LIMIT 30"
```

```bash
uv run duckdb -c "SELECT project_id, doi, output_type, publication_date, timing, cited_by_count, citations_in_window, citations_excl_self, fwci, citation_percentile, is_oa, is_review, zenodo_views, zenodo_downloads, sources FROM 'data/processed/outputs.parquet' LIMIT 30"
```

```bash
uv run duckdb -c "SELECT * FROM 'data/processed/project_metrics.parquet' LIMIT 30"
```

The coverage note is `data/processed/coverage.md`.
