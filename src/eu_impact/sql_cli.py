"""Print a DuckDB query. `uv run duckdb -c "SELECT ..."` uses this."""

from __future__ import annotations

import sys

import duckdb


def main() -> None:
    args = sys.argv[1:]
    if len(args) != 2 or args[0] != "-c":
        raise SystemExit('Usage: uv run duckdb -c "SELECT ..."')
    print(duckdb.sql(args[1]))


if __name__ == "__main__":
    main()
