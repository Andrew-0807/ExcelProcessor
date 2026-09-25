"""Tiny colored console logging. Quiet by default.

Set MOM_VERBOSE=1 to see info/debug chatter (per-step logs, skipped rows, etc).
Warnings and errors always show.

    from app.log import info, warn, err
    info("loaded 42 rows")          # only with MOM_VERBOSE
    warn("no TVA column, skipping") # always, yellow
    err("bad file", where="errors/adaos/")  # always, red + where to look

info/warn/err accept multiple args like print(), so a noisy module can silence
its debug chatter with one line: `from app.log import info as print`.
"""

import logging
import os

from rich.console import Console
from rich.logging import RichHandler

VERBOSE = os.environ.get("MOM_VERBOSE", "").lower() not in ("", "0", "false", "no")

_out = Console(stderr=True)

# Route stdlib logging (e.g. cardcec's logger) through rich, quiet unless verbose.
# force=True so this wins regardless of module import order.
logging.basicConfig(
    level=logging.DEBUG if VERBOSE else logging.WARNING,
    format="%(message)s",
    handlers=[RichHandler(console=_out, show_time=VERBOSE, show_path=VERBOSE, markup=False)],
    force=True,
)


# markup=False everywhere: data may contain "[" which rich would mis-parse.
def info(*args) -> None:
    if VERBOSE:
        _out.print(*args, style="dim", markup=False)


def warn(*args) -> None:
    _out.print("!", *args, style="yellow", markup=False)


def err(*args, where=None) -> None:
    _out.print("x", *args, style="bold red", markup=False)
    if where:
        _out.print(f"  -> look in {where}", style="blue", markup=False)
