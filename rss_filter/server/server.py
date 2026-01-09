"""FastAPI server for filtering and serving RSS feeds."""
from fastapi import FastAPI
from typing import Dict
from collections import defaultdict
import logging
import time

from ..config import load_config
from .cache import set_cache_config
from .routes import router, set_router_config
from .. import __version__

logger = logging.getLogger(__name__)

# Configuration
config = load_config()

# Cache configuration
CACHE_MAX_AGE = config["cache"]["max_age_seconds"]
CACHE_MAX_SIZE_MB = config["cache"]["max_size_mb"]
MAX_PAYLOAD_SIZE_MB = config["network"]["max_payload_mb"]
REQUEST_TIMEOUT = config["network"]["request_timeout_seconds"]
RATE_LIMIT_REQUESTS = config["rate_limiting"]["requests_per_window"]
RATE_LIMIT_WINDOW = config["rate_limiting"]["window_seconds"]
DEFAULT_HOST = config["server"]["host"]
DEFAULT_PORT = config["server"]["port"]
USER_AGENT_CONTACT_INFO = config["user_agent"]["contact_info"]

USER_AGENT = f"python-rss-filter/{__version__} ({USER_AGENT_CONTACT_INFO})"

# Initialize cache module
set_cache_config(CACHE_MAX_AGE, CACHE_MAX_SIZE_MB, MAX_PAYLOAD_SIZE_MB)


class RateLimiter:
    """Simple in-memory rate limiter by source IP."""
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > cutoff]
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        self.requests[client_ip].append(now)
        return True


class Metrics:
    """In-memory metrics tracking."""
    def __init__(self):
        self.requests_total = 0
        self.requests_success = 0
        self.requests_error = 0
        self.requests_rate_limited = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.filters_applied = 0
        self.items_removed = 0

    def to_dict(self):
        return {
            "requests_total": self.requests_total,
            "requests_success": self.requests_success,
            "requests_error": self.requests_error,
            "requests_rate_limited": self.requests_rate_limited,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "filters_applied": self.filters_applied,
            "items_removed": self.items_removed,
        }


# Initialize services
rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)
metrics = Metrics()

# Create FastAPI app
app = FastAPI()
app.include_router(router)

# Configure router with dependencies
set_router_config(metrics, rate_limiter, REQUEST_TIMEOUT, USER_AGENT)


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    """Start the RSS filter server."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger.info(f"Starting RSS filter server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
