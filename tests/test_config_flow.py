"""Tests for the QualiteEau config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ha_q_eau.api.exceptions import HubEauApiError, HubEauNoDataError
from custom_components.ha_q_eau.config_flow import _probe_commune, QualiteEauConfigFlow

from .conftest import MOCK_CODE_COMMUNE, MOCK_NOM_COMMUNE, MOCK_COMMUNE_UDI_RESPONSE


class TestProbeCommune:
    """Unit tests for _probe_commune — no hass fixture, no thread leak."""

    async def test_valid_commune_returns_name(self):
        session = MagicMock()
        with patch(
            "custom_components.ha_q_eau.config_flow.HubEauClient"
        ) as mock_cls:
            client = mock_cls.return_value
            client.async_get_communes_udi = AsyncMock(return_value=MOCK_COMMUNE_UDI_RESPONSE)
            result = await _probe_commune(session, MOCK_CODE_COMMUNE)
        assert result == MOCK_NOM_COMMUNE

    async def test_empty_data_raises_no_data_error(self):
        session = MagicMock()
        with patch(
            "custom_components.ha_q_eau.config_flow.HubEauClient"
        ) as mock_cls:
            client = mock_cls.return_value
            client.async_get_communes_udi = AsyncMock(return_value={"count": 0, "data": []})
            with pytest.raises(HubEauNoDataError):
                await _probe_commune(session, "99999")

    async def test_api_error_propagates(self):
        session = MagicMock()
        with patch(
            "custom_components.ha_q_eau.config_flow.HubEauClient"
        ) as mock_cls:
            client = mock_cls.return_value
            client.async_get_communes_udi = AsyncMock(side_effect=HubEauApiError(503))
            with pytest.raises(HubEauApiError):
                await _probe_commune(session, MOCK_CODE_COMMUNE)

    async def test_returns_code_when_nom_commune_missing(self):
        session = MagicMock()
        raw = {"count": 1, "data": [{"code_commune": "75056", "nom_commune": None}]}
        with patch(
            "custom_components.ha_q_eau.config_flow.HubEauClient"
        ) as mock_cls:
            client = mock_cls.return_value
            client.async_get_communes_udi = AsyncMock(return_value=raw)
            result = await _probe_commune(session, "75056")
        assert result == "75056"
