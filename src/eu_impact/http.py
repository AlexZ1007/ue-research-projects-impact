"""HTTP session with retries, a short pause, and a raw-file cache."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from eu_impact.config import mailto

log = logging.getLogger(__name__)


class CachedClient:
    def __init__(self, pause_seconds: float) -> None:
        contact = mailto() or "unset"
        self.pause_seconds = pause_seconds
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"eu-impact-pilot/0.1 (mailto:{contact})"
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self._last_request = 0.0

    def download(self, url: str, dest: Path) -> Path:
        if dest.exists() and dest.stat().st_size > 0:
            log.info("reuse %s", dest.name)
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        self._wait()
        log.info("download %s", url)
        with self.session.get(url, timeout=120, stream=True) as response:
            response.raise_for_status()
            with dest.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        handle.write(chunk)
        return dest

    def get_json(self, url: str, params: dict, cache_path: Path) -> dict:
        cached = _read_cache(cache_path)
        if cached is not None:
            return cached
        self._wait()
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(response.content)
        return response.json()

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if self._last_request and elapsed < self.pause_seconds:
            time.sleep(self.pause_seconds - elapsed)
        self._last_request = time.monotonic()


def _read_cache(path: Path) -> dict | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        log.warning("ignoring unreadable cache %s", path)
        return None
