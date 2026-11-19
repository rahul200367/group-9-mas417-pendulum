# AI-GENERATED (Claude Opus 5.5, 2026-11-19). See AI_USE_LOG.md.
"""Exceptions that decide what happens to an order.

* OrderRejected  -> the order can never be produced as asked (bad input, impossible period).
* OrderPostponed -> the order may be produced later (Spoolman down, not enough filament).
"""


class OrderRejected(Exception):
    """The order cannot be produced. The message is shown to the customer."""


class OrderPostponed(Exception):
    """The order cannot be produced right now. The message is shown to the customer."""


class SpoolmanError(Exception):
    """Spoolman answered, but with an error (e.g. 404 unknown spool)."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class SpoolmanUnavailable(SpoolmanError):
    """Spoolman did not answer at all (not started, wrong URL, timeout)."""
