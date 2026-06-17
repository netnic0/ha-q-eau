"""Typed exception hierarchy for the Hub'Eau API client."""

from __future__ import annotations


class HubEauError(Exception):
    """Base class for all Hub'Eau errors."""


class HubEauApiError(HubEauError):
    """Unexpected HTTP error from the Hub'Eau API."""

    def __init__(self, status: int, message: str = "") -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


class HubEauNoDataError(HubEauError):
    """The API returned an empty or unexpected payload."""
