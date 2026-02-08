"""Package-local logging utilities.

This package is a library first. By default it emits no logs unless the host
application configures logging. CLI users can opt into logs via
``NORMCORE_LOG_LEVEL``.
"""

from __future__ import annotations

import logging
import os

LOGGER_NAME = "normcore"
logger = logging.getLogger(LOGGER_NAME)
logger.addHandler(logging.NullHandler())


def configure_logging(level: str | None = None) -> None:
    """Configure package logging for CLI/runtime diagnostics.

    This is intentionally opt-in. If neither ``level`` nor
    ``NORMCORE_LOG_LEVEL`` is provided, configuration is skipped.
    """
    env_level = os.getenv("NORMCORE_LOG_LEVEL", "")
    raw_level = level if level is not None else (env_level or "")
    resolved_level = raw_level.strip()
    pkg_logger = logging.getLogger(LOGGER_NAME)
    # Always reset handlers to avoid stale stderr streams across repeated CLI calls.
    pkg_logger.handlers = []

    if not resolved_level:
        pkg_logger.addHandler(logging.NullHandler())
        pkg_logger.setLevel(logging.NOTSET)
        pkg_logger.propagate = False
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    pkg_logger.addHandler(handler)
    pkg_logger.setLevel(getattr(logging, resolved_level.upper(), logging.INFO))
    pkg_logger.propagate = False
