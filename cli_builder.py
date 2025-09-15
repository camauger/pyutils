"""Minimal CLI builder using Typer with logging and typed options."""

from __future__ import annotations

import logging
import sys
from typing import Optional

import typer

app = typer.Typer(help="Utility CLI built with Typer.")
logger = logging.getLogger(__name__)


def configure_logging(level: str) -> None:
    """Configure root logging with the given level name."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )


@app.callback()
def main(
    log_level: str = typer.Option(
        "INFO", "--log-level", help="Logging verbosity", case_sensitive=False
    ),
) -> None:
    """Global options for the CLI."""
    configure_logging(log_level)


@app.command()
def greet(
    name: str = typer.Argument(..., help="Name to greet"),
    shout: bool = typer.Option(False, "--shout", help="Uppercase the greeting"),
    repeat: int = typer.Option(1, "--repeat", min=1, help="Repeat count"),
    punctuation: Optional[str] = typer.Option(
        "!", "--punct", help="Punctuation to end the greeting"
    ),
) -> None:
    """Greet a person with optional transformations."""
    base = f"Hello {name}{punctuation or ''}"
    message = base.upper() if shout else base
    for _ in range(repeat):
        typer.echo(message)
    logger.debug("Greeting emitted", extra={"name": name, "repeat": repeat})


if __name__ == "__main__":
    app()
