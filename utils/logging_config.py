"""
Configuracao de logging da aplicacao.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask


def configure_logging(app: Flask, *, level_name: str, log_dir: str) -> None:
    """
    Configura logging em arquivo rotativo e console.
    """
    level = getattr(logging, (level_name or "INFO").upper(), logging.INFO)
    destination = Path(log_dir)
    destination.mkdir(parents=True, exist_ok=True)

    log_file = destination / "backend.log"
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    app.logger.handlers.clear()
    app.logger.setLevel(level)
    app.logger.propagate = False
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
