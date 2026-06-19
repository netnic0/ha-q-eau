"""Tests for the diagnostics platform (Silver tier)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.ha_q_eau.const import CONF_CODE_COMMUNE, CONF_NOM_COMMUNE, DOMAIN
from custom_components.ha_q_eau.diagnostics import (
    _dataclass_to_jsonable,
    _dump_data,
    async_get_config_entry_diagnostics,
)

from .conftest import (
    MOCK_CODE_COMMUNE,
    MOCK_COMMUNE_UDI_RESPONSE,
    MOCK_LATEST_RESULT_RESPONSE,
    MOCK_NOM_COMMUNE,
    MOCK_PARAMS_RESPONSE,
)


async def _setup_integration(hass: HomeAssistant):
    """Helper: create and load a config entry — mirrors test_init.py."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE,
            CONF_NOM_COMMUNE: MOCK_NOM_COMMUNE,
        },
        unique_id=MOCK_CODE_COMMUNE,
        version=1,
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.ha_q_eau.api.client.HubEauClient.async_get_communes_udi",
            new=AsyncMock(return_value=MOCK_COMMUNE_UDI_RESPONSE),
        ),
        patch(
            "custom_components.ha_q_eau.api.client.HubEauClient.async_get_latest_result",
            new=AsyncMock(return_value=MOCK_LATEST_RESULT_RESPONSE),
        ),
        patch(
            "custom_components.ha_q_eau.api.client.HubEauClient.async_get_recent_parameters",
            new=AsyncMock(return_value=MOCK_PARAMS_RESPONSE),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry


class TestAsyncGetConfigEntryDiagnostics:
    async def test_returns_entry_section(self, hass: HomeAssistant):
        entry = await _setup_integration(hass)
        diag = await async_get_config_entry_diagnostics(hass, entry)
        assert diag["entry"]["unique_id"] == MOCK_CODE_COMMUNE
        assert diag["entry"]["data"][CONF_CODE_COMMUNE] == MOCK_CODE_COMMUNE
        assert diag["entry"]["version"] == 1

    async def test_returns_coordinator_section(self, hass: HomeAssistant):
        entry = await _setup_integration(hass)
        diag = await async_get_config_entry_diagnostics(hass, entry)
        coord = diag["coordinator"]
        assert coord["last_update_success"] is True
        assert coord["update_interval_seconds"] == 24 * 3600
        assert coord["data"] is not None

    async def test_dumps_commune_info_and_parameters(self, hass: HomeAssistant):
        entry = await _setup_integration(hass)
        diag = await async_get_config_entry_diagnostics(hass, entry)
        data = diag["coordinator"]["data"]
        assert data["commune_info"]["code_commune"] == MOCK_CODE_COMMUNE
        # Parameters should be a list of dicts (not dataclasses) with expected fields.
        params = data["parameters"]
        assert isinstance(params, list)
        assert len(params) >= 1
        first = params[0]
        assert "code_parametre" in first
        assert "resultat_numerique" in first
        # Datetime serialised to ISO string.
        assert isinstance(first["date_prelevement"], str)
        assert "T" in first["date_prelevement"]

    async def test_returns_none_data_when_coordinator_missing(
        self, hass: HomeAssistant
    ):
        """Entry without an active coordinator (edge case) returns None for data.

        Models the pre-setup / ghost-entry scenario: the entry exists but
        `async_setup_entry` has not run, so `runtime_data` was never set.
        Diagnostics must not crash and must report None for both data and
        last_update_success.
        """
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "ghost_entry"
        entry.title = "Ghost"
        entry.version = 1
        entry.minor_version = 1
        entry.data = {CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE}
        entry.options = {}
        entry.unique_id = MOCK_CODE_COMMUNE
        # Explicitly clear runtime_data — MagicMock(spec=ConfigEntry) auto-creates
        # the attribute as another MagicMock if it exists on the spec class, and
        # we want a deterministic None to exercise the diagnostics fallback path.
        entry.runtime_data = None

        diag = await async_get_config_entry_diagnostics(hass, entry)
        assert diag["coordinator"]["data"] is None
        assert diag["coordinator"]["last_update_success"] is None


class TestHelpers:
    """Pure-unit tests for the dump helpers (no hass fixture)."""

    def test_dataclass_to_jsonable_stringifies_datetimes(self):
        from custom_components.ha_q_eau.api.models import CommuneInfo

        info = CommuneInfo(
            code_commune="75056",
            nom_commune="PARIS",
            nom_distributeur="EAU DE PARIS",
            code_departement="75",
            reseaux=("075000221",),
        )
        result = _dataclass_to_jsonable(info)
        assert result["nom_commune"] == "PARIS"
        # tuples are accepted by asdict — kept as list-like in the dump.
        assert "reseaux" in result

    def test_dump_data_returns_none_when_coordinator_data_missing(self):
        coord = MagicMock()
        coord.data = None
        assert _dump_data(coord) is None

    def test_dump_data_returns_none_when_coordinator_is_none(self):
        assert _dump_data(None) is None
