"""Tests for the HubEauClient API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.ha_q_eau.api.client import HubEauClient
from custom_components.ha_q_eau.api.exceptions import HubEauApiError, HubEauNoDataError

from .conftest import (
    MOCK_CODE_COMMUNE,
    MOCK_COMMUNE_UDI_RESPONSE,
    MOCK_LATEST_RESULT_RESPONSE,
    MOCK_PARAMS_RESPONSE,
)


def _make_mock_response(status: int, json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    resp.text = AsyncMock(return_value="")
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


@pytest.fixture
def mock_session():
    session = MagicMock(spec=aiohttp.ClientSession)
    return session


class TestHubEauClient:
    """Tests for HubEauClient."""

    async def test_get_communes_udi_success(self, mock_session):
        resp = _make_mock_response(200, MOCK_COMMUNE_UDI_RESPONSE)
        mock_session.get = MagicMock(return_value=resp)
        client = HubEauClient(mock_session)

        result = await client.async_get_communes_udi(MOCK_CODE_COMMUNE)

        assert result["count"] == 2
        assert result["data"][0]["nom_commune"] == "PARIS"

    async def test_get_communes_udi_http_error(self, mock_session):
        resp = _make_mock_response(500, {})
        resp.text = AsyncMock(return_value="Internal Server Error")
        mock_session.get = MagicMock(return_value=resp)
        client = HubEauClient(mock_session)

        with pytest.raises(HubEauApiError) as exc_info:
            await client.async_get_communes_udi(MOCK_CODE_COMMUNE)
        assert exc_info.value.status == 500

    async def test_get_latest_result_success(self, mock_session):
        resp = _make_mock_response(200, MOCK_LATEST_RESULT_RESPONSE)
        mock_session.get = MagicMock(return_value=resp)
        client = HubEauClient(mock_session)

        result = await client.async_get_latest_result(MOCK_CODE_COMMUNE)

        assert result["data"][0]["conformite_limites_bact_prelevement"] == "C"

    async def test_get_latest_result_empty_raises(self, mock_session):
        resp = _make_mock_response(200, {"count": 0, "data": []})
        mock_session.get = MagicMock(return_value=resp)
        client = HubEauClient(mock_session)

        with pytest.raises(HubEauNoDataError):
            await client.async_get_latest_result(MOCK_CODE_COMMUNE)

    async def test_get_recent_parameters_success(self, mock_session):
        resp = _make_mock_response(200, MOCK_PARAMS_RESPONSE)
        mock_session.get = MagicMock(return_value=resp)
        client = HubEauClient(mock_session)

        result = await client.async_get_recent_parameters(MOCK_CODE_COMMUNE)

        assert len(result["data"]) == 4

    async def test_validate_commune_true(self, mock_session):
        resp = _make_mock_response(200, MOCK_COMMUNE_UDI_RESPONSE)
        mock_session.get = MagicMock(return_value=resp)
        client = HubEauClient(mock_session)

        assert await client.async_validate_commune(MOCK_CODE_COMMUNE) is True

    async def test_validate_commune_false_on_empty(self, mock_session):
        resp = _make_mock_response(200, {"count": 0, "data": []})
        mock_session.get = MagicMock(return_value=resp)
        client = HubEauClient(mock_session)

        assert await client.async_validate_commune("99999") is False

    async def test_validate_commune_false_on_error(self, mock_session):
        resp = _make_mock_response(404, {})
        resp.text = AsyncMock(return_value="Not Found")
        mock_session.get = MagicMock(return_value=resp)
        client = HubEauClient(mock_session)

        assert await client.async_validate_commune("00000") is False
