"""Load pilot config and project paths."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
CONFIG_PATH = ROOT / "config" / "pilot.yaml"

load_dotenv(ROOT / ".env")


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def mailto() -> str:
    return os.environ.get("OPENALEX_MAILTO", "").strip()


def openalex_api_key() -> str:
    return os.environ.get("OPENALEX_API_KEY", "").strip()
