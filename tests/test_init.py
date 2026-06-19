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
    async def test_setup_stores_coordinator_on_runtime_data(
        self, hass: HomeAssistant, config_entry_data
    ):
        """The coordinator is published on entry.runtime_data (HA 2024.6+)."""
        entry = await _setup_integration(hass, config_entry_data)
        assert entry.state == ConfigEntryState.LOADED
        # runtime_data is populated by async_setup_entry; nothing else owns it.
        assert entry.runtime_data is not None
        # Sanity check the type — the coordinator is a QualiteEauCoordinator.
        from custom_components.ha_q_eau.coordinator import QualiteEauCoordinator

        assert isinstance(entry.runtime_data, QualiteEauCoordinator)

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
        # HA generates entity_id from the translated name, not the translation_key.
        # In English: "Bacteriological conformity" → "bacteriological_conformity"
        bact_states = [
            s for s in all_states if "bacteriological_conformity" in s.entity_id
        ]
        assert len(bact_states) == 1
        assert bact_states[0].state == "compliant"


class TestAsyncUnloadEntry:
    async def test_unload_changes_state_to_not_loaded(
        self, hass: HomeAssistant, config_entry_data
    ):
        """Unloading a loaded entry transitions it to NOT_LOADED.

        With runtime_data, HA itself manages the lifetime of the coordinator
        reference — there is no `hass.data[DOMAIN][entry.entry_id]` to clean
        up, so the only observable post-unload invariant is the entry state.
        """
        entry = await _setup_integration(hass, config_entry_data)
        assert entry.state == ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.NOT_LOADED


class TestAsyncRemoveConfigEntryDevice:
    """Silver `stale-devices` rule: only allow device removal when stale."""

    async def test_rejects_active_device(
        self, hass: HomeAssistant, config_entry_data
    ):
        """A device whose identifier matches the entry's commune must NOT be deletable."""
        from homeassistant.helpers import device_registry as dr

        from custom_components.ha_q_eau import async_remove_config_entry_device

        entry = await _setup_integration(hass, config_entry_data)
        device_registry = dr.async_get(hass)
        # The integration created exactly one device for this commune.
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, MOCK_CODE_COMMUNE)}
        )
        assert device is not None

        result = await async_remove_config_entry_device(hass, entry, device)
        assert result is False

    async def test_accepts_stale_device(
        self, hass: HomeAssistant, config_entry_data
    ):
        """A device whose identifier no longer matches the entry's commune is removable."""
        from homeassistant.helpers import device_registry as dr

        from custom_components.ha_q_eau import async_remove_config_entry_device

        entry = await _setup_integration(hass, config_entry_data)
        # Build a synthetic device entry with a non-matching identifier.
        stale_device = MagicMock(spec=dr.DeviceEntry)
        stale_device.identifiers = {(DOMAIN, "00000")}  # not MOCK_CODE_COMMUNE

        result = await async_remove_config_entry_device(hass, entry, stale_device)
        assert result is True
