"""ha_q_eau integration entry point."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HubEauClient
from .const import CONF_CODE_COMMUNE, DOMAIN
from .coordinator import QualiteEauConfigEntry, QualiteEauCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: QualiteEauConfigEntry) -> bool:
    """Set up ha_q_eau from a config entry.

    Stores the coordinator on `entry.runtime_data` (HA 2024.6+ pattern). HA
    clears this attribute automatically when the entry unloads, so no manual
    cleanup is required in `async_unload_entry`.
    """
    session = async_get_clientsession(hass)
    client = HubEauClient(session)

    coordinator = QualiteEauCoordinator(hass, client, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: QualiteEauConfigEntry) -> bool:
    """Unload a config entry.

    `entry.runtime_data` is HA-managed: it is cleared automatically when the
    entry is unloaded, so we only need to drive the platform unload here.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry to current schema.

    Today there is only schema v1. The version guard below is forward-defensive:
    if a future release introduces v2 but this function is still the v1 stub,
    HA must refuse the downgrade rather than silently accept it.

    Note: this function runs BEFORE `async_setup_entry`, so `entry.runtime_data`
    is not populated yet — keep the bare `ConfigEntry` annotation here.
    """
    if entry.version > 1:
        _LOGGER.error(
            "Cannot downgrade from config entry version %s to 1", entry.version
        )
        return False
    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removal of a device only when it no longer matches the active entry.

    This integration creates exactly one device per config entry, identified by
    `(DOMAIN, code_commune)`. As long as that identifier matches the active entry,
    the device represents the current commune and must NOT be deletable from the
    HA UI — otherwise the entity would re-appear orphaned on next refresh.

    A device whose identifier no longer matches the entry's commune (e.g. left
    over after a future commune change) is safe to delete.

    Note: this function reads only `config_entry.data`, not `runtime_data` —
    keep the bare `ConfigEntry` annotation here.
    """
    code_commune = config_entry.data.get(CONF_CODE_COMMUNE)
    active_identifier = (DOMAIN, code_commune)
    return active_identifier not in device_entry.identifiers


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change.

    Triggers a full setup/unload cycle — does not access `runtime_data`.
    """
    await hass.config_entries.async_reload(entry.entry_id)
