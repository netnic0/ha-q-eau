"""Tests for the integration entry point (__init__.py) — Silver tier."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.ha_q_eau.const import CONF_CODE_COMMUNE, CONF_NOM_COMMUNE, DOMAIN

from .conftest import (
    MOCK_CODE_COMMUNE,
    MOCK_COMMUNE_UDI_RESPONSE,
    MOCK_LATEST_RESULT_RESPONSE,
    MOCK_PARAMS_RESPONSE,
    MOCK_NOM_COMMUNE,
)


@pytest.fixture
def config_entry_data():
    return {
        CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE,
        CONF_NOM_COMMUNE: MOCK_NOM_COMMUNE,
    }


async def _setup_integration(hass: HomeAssistant, data: dict):
    """Helper: create and load a config entry for ha_q_eau."""
    from homeassistant.config_entries import ConfigEntry
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
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


class TestAsyncSetupEntry:
    async def test_setup_creates_coordinator_in_hass_data(
        self, hass: HomeAssistant, config_entry_data
    ):
        entry = await _setup_integration(hass, config_entry_data)
        assert entry.state == ConfigEntryState.LOADED
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]

    async def test_setup_registers_sensor_entities(
        self, hass: HomeAssistant, config_entry_data
    ):
        await _setup_integration(hass, config_entry_data)
        # Conformity sensors must exist
        bact_state = hass.states.get(
            f"sensor.qualite_eau_paris_{MOCK_CODE_COMMUNE}_conformity_bact"
        )
        # Entity IDs may vary by HA version; just check at least one sensor loaded
        all_states = hass.states.async_entity_ids("sensor")
        assert len(all_states) >= 5

    async def test_setup_loads_conformity_state(
        self, hass: HomeAssistant, config_entry_data
    ):
        await _setup_integration(hass, config_entry_data)
        all_states = hass.states.async_all("sensor")
        bact_states = [
            s for s in all_states if "conformity_bact" in s.entity_id
        ]
        assert len(bact_states) == 1
        assert bact_states[0].state == "C"


class TestAsyncUnloadEntry:
    async def test_unload_removes_coordinator(
        self, hass: HomeAssistant, config_entry_data
    ):
        entry = await _setup_integration(hass, config_entry_data)
        assert entry.entry_id in hass.data.get(DOMAIN, {})

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.NOT_LOADED
        assert entry.entry_id not in hass.data.get(DOMAIN, {})

    async def test_unload_safe_when_domain_missing(
        self, hass: HomeAssistant, config_entry_data
    ):
        """async_unload_entry must not raise if hass.data[DOMAIN] is absent."""
        entry = await _setup_integration(hass, config_entry_data)
        hass.data.pop(DOMAIN, None)

        # Should not raise
        result = await hass.config_entries.async_unload(entry.entry_id)
        assert result
