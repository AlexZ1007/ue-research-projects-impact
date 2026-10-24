"""Grant ids and DOIs, shared by every source."""

from __future__ import annotations

import re

_DOI = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+", re.IGNORECASE)
_GRANT_DOI = re.compile(r"10\.3030/(\d+)", re.IGNORECASE)
_PROJECT_URL = re.compile(r"project/id/(\d+)", re.IGNORECASE)
_NOT_OUTPUT_DOI = ("10.13039/", "10.3030/")


def normalize_grant_id(value: object) -> str | None:
    """Return the CORDIS grant agreement number, or None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>"}:
        return None
    if "::" in text:
        text = text.split("::")[-1].strip()
    match = _PROJECT_URL.search(text)
    if match:
        return match.group(1)
    match = _GRANT_DOI.search(text)
    if match:
        return match.group(1)
    text = re.sub(r"^(GA|grant)\s*", "", text, flags=re.IGNORECASE).strip()
    if text.isdigit():
        return text
    return None


def normalize_doi(value: object) -> str | None:
    """Return a lowercase output DOI, without a resolver prefix.

    Grant DOIs (10.3030) and Crossref funder ids (10.13039) are rejected.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^urn:doi:", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^doi:", "", text, flags=re.IGNORECASE)
    match = _DOI.search(text)
    if not match:
        return None
    doi = match.group(0).rstrip(").,;").lower()
    if doi.startswith(_NOT_OUTPUT_DOI):
        return None
    return doi


def extract_dois(value: object) -> list[str]:
    if value is None:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for match in _DOI.finditer(str(value)):
        doi = normalize_doi(match.group(0))
        if doi and doi not in seen:
            seen.add(doi)
            found.append(doi)
    return found
