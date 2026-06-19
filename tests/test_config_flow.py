"""Tests for the QualiteEau config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ha_q_eau.api.exceptions import HubEauApiError, HubEauNoDataError
from custom_components.ha_q_eau.config_flow import _probe_commune

from .conftest import MOCK_CODE_COMMUNE, MOCK_NOM_COMMUNE, MOCK_COMMUNE_UDI_RESPONSE


def _make_client(*, return_value=None, side_effect=None) -> MagicMock:
    """Build a mock HubEauClient with a stubbed async_get_communes_udi."""
    client = MagicMock()
    client.async_get_communes_udi = AsyncMock(
        return_value=return_value, side_effect=side_effect
    )
    return client


class TestProbeCommune:
    """Unit tests for _probe_commune — no hass fixture, no thread leak.

    The client is now injected (was constructed inside the function before),
    so tests pass a MagicMock directly instead of patching the constructor.
    """

    async def test_valid_commune_returns_name(self):
        client = _make_client(return_value=MOCK_COMMUNE_UDI_RESPONSE)
        result = await _probe_commune(client, MOCK_CODE_COMMUNE)
        assert result == MOCK_NOM_COMMUNE

    async def test_empty_data_raises_no_data_error(self):
        client = _make_client(return_value={"count": 0, "data": []})
        with pytest.raises(HubEauNoDataError):
            await _probe_commune(client, "99999")

    async def test_api_error_propagates(self):
        client = _make_client(side_effect=HubEauApiError(503))
        with pytest.raises(HubEauApiError):
            await _probe_commune(client, MOCK_CODE_COMMUNE)

    async def test_returns_code_when_nom_commune_missing(self):
        raw = {"count": 1, "data": [{"code_commune": "75056", "nom_commune": None}]}
        client = _make_client(return_value=raw)
        result = await _probe_commune(client, "75056")
        assert result == "75056"
