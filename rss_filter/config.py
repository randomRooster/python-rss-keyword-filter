"""Configuration loading for the RSS filter server."""
import os
import logging

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python < 3.11

logger = logging.getLogger(__name__)

# Configuration defaults
DEFAULT_CONFIG = {
    "cache": {
        "max_age_seconds": 86400,
        "max_size_mb": 500,
    },
    "network": {
        "request_timeout_seconds": 30,
        "max_payload_mb": 50,
    },
    "rate_limiting": {
        "requests_per_window": 100,
        "window_seconds": 3600,
    },
    "server": {
        "host": "127.0.0.1",
        "port": 8000,
    },
    "user_agent": {
        "contact_info": "an-impolite-user@example.com",
    },
}


def load_config(config_path: str = "config.toml") -> dict:
    """Load configuration from TOML file with fallback to defaults."""
    if not os.path.exists(config_path):
        logger.warning(f"Config file {config_path} not found, using defaults")
        return DEFAULT_CONFIG

    try:
        with open(config_path, "rb") as fh:
            config = tomllib.load(fh)
        logger.info(f"Loaded configuration from {config_path}")
        # Merge with defaults to fill in any missing keys
        merged = DEFAULT_CONFIG.copy()
        for section, values in config.items():
            if section in merged:
                merged[section].update(values)
            else:
                merged[section] = values
        return merged
    except Exception as exc:
        logger.error(f"Failed to load config from {config_path}: {exc}, using defaults")
        return DEFAULT_CONFIG
