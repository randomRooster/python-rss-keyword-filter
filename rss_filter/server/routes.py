"""API routes for the RSS filter server."""
from fastapi import APIRouter, Query, Response, HTTPException, Request
from typing import Optional
import logging
import httpx

from ..feed import filter_bytes
from .cache import fetch_with_cache, get_cache_size_mb

logger = logging.getLogger(__name__)

router = APIRouter()

# TODO: turn this into a class. This is lazy even by my standards.
# Will be set by server module
metrics = None
rate_limiter = None
request_timeout = 30
user_agent = "python-rss-filter/0.1.0"


def set_router_config(metrics_obj, rate_limiter_obj, timeout: int, ua: str):
    """Configure router with dependencies."""
    global metrics, rate_limiter, request_timeout, user_agent
    metrics = metrics_obj
    rate_limiter = rate_limiter_obj
    request_timeout = timeout
    user_agent = ua


@router.get("/filter")
async def filter_endpoint(
    request: Request,
    source: str = Query(..., description="URL of the RSS feed to fetch"),
    include: Optional[str] = Query(None, description="Comma-separated include keywords"),
    exclude: Optional[str] = Query(None, description="Comma-separated exclude keywords"),
    regex: Optional[str] = Query(None, description="Regex to match keywords text"),
):
    """Filter RSS feed items by keywords."""
    client_ip = request.client.host if request.client else "unknown"
    metrics.requests_total += 1

    # Rate limiting
    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for {client_ip}")
        metrics.requests_rate_limited += 1
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    includes = [p.strip() for p in include.split(",")] if include else None
    excludes = [p.strip() for p in exclude.split(",")] if exclude else None

    logger.info(f"Filter request from {client_ip}: source={source}, include={includes}, exclude={excludes}, regex={regex}")

    try:
        async with httpx.AsyncClient(timeout=request_timeout, follow_redirects=True) as client:
            content_bytes, meta = await fetch_with_cache(source, client)
        out = filter_bytes(content_bytes, include=includes, exclude=excludes, regex=regex, original_source=source)
        metrics.requests_success += 1
        metrics.filters_applied += 1
        logger.info(f"Filter completed successfully for {client_ip}: {len(out)} bytes output")
        return Response(content=out, media_type="application/rss+xml")
    except Exception as exc:
        metrics.requests_error += 1
        logger.exception(f"Error processing filter request from {client_ip}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
async def health_endpoint():
    """Basic health check endpoint."""
    return {"status": "healthy", "cache_size_mb": get_cache_size_mb()}


@router.get("/metrics")
async def metrics_endpoint():
    """Metrics endpoint returning current server metrics as JSON."""
    return {
        **metrics.to_dict(),
        "cache_size_mb": get_cache_size_mb(),
    }
