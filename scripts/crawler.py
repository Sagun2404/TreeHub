"""
TreeHub Crawler — llms.txt fetcher with rate limiting and caching.

Usage:
    python scripts/crawler.py --platform supabase --url https://supabase.com/llms.txt
    python scripts/crawler.py --platform supabase --url https://supabase.com/llms.txt --output ./output/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CACHE_DIR = Path.home() / ".treehub" / "cache" / "crawl"
DEFAULT_OUTPUT_DIR = Path("indices")
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
BACKOFF_FACTOR = 2.0
REQUEST_TIMEOUT = 30.0  # seconds
USER_AGENT = "TreeHub-Crawler/1.0 (+https://github.com/treehub/indices)"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CrawlResult:
    """Result of a single crawl operation."""

    platform: str
    source_url: str
    content: str
    content_hash: str
    fetched_at: str
    cached: bool = False
    status_code: int = 200


@dataclass
class CrawlerConfig:
    """Configuration for the crawler."""

    cache_dir: Path = field(default_factory=lambda: DEFAULT_CACHE_DIR)
    output_dir: Path = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)
    timeout: float = REQUEST_TIMEOUT
    max_retries: int = MAX_RETRIES
    respect_robots: bool = True
    user_agent: str = USER_AGENT


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------


class LlmsTxtCrawler:
    """Fetches llms.txt from platform documentation sites.

    Features:
        - Exponential backoff on failures
        - Local file caching to avoid redundant requests
        - robots.txt awareness
        - Content hashing for change detection
    """

    def __init__(self, config: CrawlerConfig | None = None) -> None:
        self.config = config or CrawlerConfig()
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)

    # -- Public API ---------------------------------------------------------

    def fetch(self, platform: str, url: str, *, force: bool = False) -> CrawlResult:
        """Fetch llms.txt content for a platform.

        Args:
            platform: Platform identifier (e.g. "supabase").
            url: URL to the llms.txt file.
            force: If True, bypass cache.

        Returns:
            CrawlResult with content and metadata.
        """
        # Check cache first
        if not force:
            cached = self._load_cache(platform)
            if cached is not None:
                logger.info("Cache hit for %s", platform)
                return cached

        # Check robots.txt
        if self.config.respect_robots and not self._check_robots(url):
            raise PermissionError(
                f"robots.txt disallows crawling {url}. "
                "Set respect_robots=False to override."
            )

        # Fetch with retry
        content = self._fetch_with_retry(url)
        content_hash = self._hash_content(content)
        now = datetime.now(timezone.utc).isoformat()

        result = CrawlResult(
            platform=platform,
            source_url=url,
            content=content,
            content_hash=f"sha256:{content_hash}",
            fetched_at=now,
        )

        # Write cache
        self._save_cache(platform, result)
        logger.info("Fetched %s (%d bytes)", platform, len(content))
        return result

    def has_changed(self, platform: str, previous_hash: str) -> bool | None:
        """Check if cached content hash differs from a previous hash.

        Returns None if no cache entry exists.
        """
        cached = self._load_cache(platform)
        if cached is None:
            return None
        return cached.content_hash != previous_hash

    # -- Internal -----------------------------------------------------------

    def _fetch_with_retry(self, url: str) -> str:
        """Fetch URL with exponential backoff retry."""
        backoff = INITIAL_BACKOFF
        last_exception: Exception | None = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                with httpx.Client(timeout=self.config.timeout) as client:
                    response = client.get(
                        url, headers={"User-Agent": self.config.user_agent}
                    )
                    response.raise_for_status()
                    return response.text
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exception = exc
                logger.warning(
                    "Attempt %d/%d failed for %s: %s",
                    attempt,
                    self.config.max_retries,
                    url,
                    exc,
                )
                if attempt < self.config.max_retries:
                    time.sleep(backoff)
                    backoff *= BACKOFF_FACTOR

        raise ConnectionError(
            f"Failed to fetch {url} after {self.config.max_retries} retries"
        ) from last_exception

    def _check_robots(self, url: str) -> bool:
        """Check if robots.txt allows crawling the URL."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(robots_url)
                if resp.status_code != 200:
                    return True  # No robots.txt → allow

                # Simple check: look for Disallow on the path
                path = parsed.path
                for line in resp.text.splitlines():
                    line = line.strip()
                    if line.lower().startswith("disallow:"):
                        disallowed = line.split(":", 1)[1].strip()
                        if disallowed and path.startswith(disallowed):
                            return False
                return True
        except httpx.RequestError:
            return True  # Can't fetch robots.txt → allow

    def _hash_content(self, content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _cache_path(self, platform: str) -> Path:
        """Return the cache file path for a platform."""
        return self.config.cache_dir / f"{platform}.json"

    def _save_cache(self, platform: str, result: CrawlResult) -> None:
        """Persist crawl result to local cache."""
        cache_file = self._cache_path(platform)
        data = {
            "platform": result.platform,
            "source_url": result.source_url,
            "content": result.content,
            "content_hash": result.content_hash,
            "fetched_at": result.fetched_at,
            "status_code": result.status_code,
        }
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_cache(self, platform: str) -> CrawlResult | None:
        """Load cached crawl result if it exists."""
        cache_file = self._cache_path(platform)
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return CrawlResult(
                platform=data["platform"],
                source_url=data["source_url"],
                content=data["content"],
                content_hash=data["content_hash"],
                fetched_at=data["fetched_at"],
                cached=True,
                status_code=data.get("status_code", 200),
            )
        except (json.JSONDecodeError, KeyError):
            logger.warning("Corrupt cache for %s, ignoring", platform)
            return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="TreeHub llms.txt Crawler")
    parser.add_argument("--platform", required=True, help="Platform identifier")
    parser.add_argument("--url", required=True, help="llms.txt URL")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR), help="Output dir")
    parser.add_argument("--force", action="store_true", help="Bypass cache")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = CrawlerConfig(output_dir=Path(args.output))
    crawler = LlmsTxtCrawler(config)
    result = crawler.fetch(args.platform, args.url, force=args.force)

    # Save raw content
    out_dir = config.output_dir / args.platform
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_file = out_dir / "llms.txt"
    raw_file.write_text(result.content, encoding="utf-8")

    print(f"✅ Crawled {args.platform}")
    print(f"   URL:    {result.source_url}")
    print(f"   Hash:   {result.content_hash}")
    print(f"   Cached: {result.cached}")
    print(f"   Saved:  {raw_file}")


if __name__ == "__main__":
    main()
