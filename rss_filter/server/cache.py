"""Caching utilities for the RSS filter server."""
import hashlib
import os
import json
import time
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Todo: turn this into a class
# Cache configuration (will be set by server module)
CACHE_DIR = ".cache"
CACHE_MAX_AGE = 86400
CACHE_MAX_SIZE_MB = 500
MAX_PAYLOAD_SIZE = 50 * 1024 * 1024


def set_cache_config(max_age: int, max_size_mb: int, max_payload_mb: int):
    """Configure cache settings from config module."""
    global CACHE_MAX_AGE, CACHE_MAX_SIZE_MB, MAX_PAYLOAD_SIZE
    CACHE_MAX_AGE = max_age
    CACHE_MAX_SIZE_MB = max_size_mb
    MAX_PAYLOAD_SIZE = max_payload_mb
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(url: str) -> str:
    """Generate cache key from URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def get_cache_size_mb() -> float:
    """Calculate total size of cache directory in MB."""
    total_size = 0
    for filename in os.listdir(CACHE_DIR):
        filepath = os.path.join(CACHE_DIR, filename)
        if os.path.isfile(filepath):
            total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)


def cleanup_old_cache_entries():
    """Remove oldest cache entries if directory exceeds size limit."""
    cache_size_mb = get_cache_size_mb()
    if cache_size_mb <= CACHE_MAX_SIZE_MB:
        return

    logger.info(f"Cache size ({cache_size_mb:.1f} MB) exceeds limit ({CACHE_MAX_SIZE_MB} MB), cleaning up old entries")
    entries = []
    for filename in os.listdir(CACHE_DIR):
        filepath = os.path.join(CACHE_DIR, filename)
        if os.path.isfile(filepath):
            mtime = os.path.getmtime(filepath)
            entries.append((mtime, filepath))

    entries.sort()
    for mtime, filepath in entries[:len(entries) // 2]:
        try:
            os.remove(filepath)
            logger.debug(f"Removed cache entry: {filepath}")
        except Exception as exc:
            logger.warning(f"Failed to remove cache entry {filepath}: {exc}")


def is_feed_content_type(content_type: str = None) -> bool:
    """Validate that content-type indicates an RSS/Atom feed."""
    if not content_type:
        return True
    content_type_lower = content_type.lower()
    return any(t in content_type_lower for t in ["rss", "atom", "xml", "feed"])


async def fetch_with_cache(url: str, httpx_client) -> Tuple[bytes, dict]:
    """Fetch feed from URL with caching and conditional requests."""
    from fastapi import HTTPException

    key = _cache_key(url)
    meta_path = os.path.join(CACHE_DIR, key + ".json")
    content_path = os.path.join(CACHE_DIR, key + ".xml")

    headers = {}
    existing_meta = {}
    cache_expired = False

    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                existing_meta = json.load(fh)
            fetched_at = existing_meta.get("fetched_at", 0)
            if time.time() - fetched_at > CACHE_MAX_AGE:
                cache_expired = True
                logger.debug(f"Cache expired for {url} (age > {CACHE_MAX_AGE}s)")
            elif existing_meta.get("etag"):
                headers["If-None-Match"] = existing_meta["etag"]
            if existing_meta.get("last_modified"):
                headers["If-Modified-Since"] = existing_meta["last_modified"]
        except Exception:
            existing_meta = {}

    try:
        resp = await httpx_client.get(url, headers=headers)
    except TimeoutError:
        logger.error(f"Timeout fetching {url}")
        raise HTTPException(status_code=504, detail="Upstream feed request timed out")
    except Exception as exc:
        logger.error(f"Error fetching {url}: {exc}")
        raise HTTPException(status_code=502, detail=f"Error fetching upstream feed: {exc}")

    if resp.status_code == 304 and os.path.exists(content_path) and not cache_expired:
        logger.info(f"Cache hit for {url}")
        with open(content_path, "rb") as fh:
            return fh.read(), existing_meta

    if resp.status_code >= 400:
        logger.error(f"Upstream error for {url}: {resp.status_code}")
        raise HTTPException(status_code=resp.status_code, detail=f"Upstream returned {resp.status_code}")

    # Validate content-type
    content_type = resp.headers.get("content-type")
    if not is_feed_content_type(content_type):
        logger.warning(f"Suspicious content-type for {url}: {content_type}")

    # Check payload size
    if len(resp.content) > MAX_PAYLOAD_SIZE:
        logger.error(f"Payload too large for {url}: {len(resp.content)} bytes")
        raise HTTPException(status_code=413, detail="Feed payload exceeds maximum allowed size")

    logger.info(f"Cache miss for {url} (fetched {len(resp.content)} bytes)")
    body = resp.content
    meta = {"fetched_at": time.time()}
    if "etag" in resp.headers:
        meta["etag"] = resp.headers["etag"]
    if "last-modified" in resp.headers:
        meta["last_modified"] = resp.headers["last-modified"]

    # Persist cache
    try:
        with open(content_path, "wb") as fh:
            fh.write(body)
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh)
        cleanup_old_cache_entries()
    except Exception as exc:
        logger.warning(f"Failed to persist cache for {url}: {exc}")

    return body, meta
