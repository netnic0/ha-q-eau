"""ha_q_eau integration entry point."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HubEauClient
from .const import DOMAIN
from .coordinator import QualiteEauCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ha_q_eau from a config entry."""
    session = async_get_clientsession(hass)
    client = HubEauClient(session)

    coordinator = QualiteEauCoordinator(hass, client, entry)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    `hass.data` cleanup is unconditional: even on partial-unload failure we drop the
    coordinator reference to avoid leaking it (mirrors the convention used by HA-core
    integrations). `dict.pop(key, None)` is safe when the entry is already absent.
    """
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry to current schema.

    Today there is only schema v1. The version guard below is forward-defensive:
    if a future release introduces v2 but this function is still the v1 stub,
    HA must refuse the downgrade rather than silently accept it.
    """
    if entry.version > 1:
        _LOGGER.error(
            "Cannot downgrade from config entry version %s to 1", entry.version
        )
        return False
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
