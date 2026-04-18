"""Structured JSON logging to stdout (captured by journald in prod)."""

from __future__ import annotations

import logging

import structlog


def configure() -> None:
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
    )


logger = structlog.get_logger()
