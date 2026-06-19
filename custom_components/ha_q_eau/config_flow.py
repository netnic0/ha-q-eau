"""Config flow and options flow for the ha_q_eau integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HubEauApiError, HubEauClient, HubEauNoDataError
from .const import (
    CONF_CODE_COMMUNE,
    CONF_NOM_COMMUNE,
    DEFAULT_SCAN_INTERVAL_H,
    DOMAIN,
    OPT_SCAN_INTERVAL_H,
    OPT_SCAN_INTERVAL_H_MAX,
    OPT_SCAN_INTERVAL_H_MIN,
)
_LOGGER = logging.getLogger(__name__)

_STEP_USER_SCHEMA = vol.Schema(
    {
        # INSEE commune code is exactly 5 digits (e.g. Paris=75056, Lyon-1=69123).
        # Strip whitespace first so " 75056 " is accepted; then validate the digit pattern
        # client-side to avoid a needless API round-trip on obviously invalid input.
        vol.Required(CONF_CODE_COMMUNE): vol.All(
            str,
            lambda v: v.strip(),
            vol.Match(r"^\d{5}$"),
        ),
    }
)


async def _probe_commune(client: HubEauClient, code_commune: str) -> str:
    """Validate the INSEE code and return the commune name.

    The client is injected so the function stays testable without patching
    the HubEauClient constructor and so the canonical client construction
    happens in a single place (async_step_user → async_get_clientsession).

    Raises:
        HubEauNoDataError: code_commune returns no UDI records.
        HubEauApiError: HTTP error from the Hub'Eau API.
    """
    raw = await client.async_get_communes_udi(code_commune)
    records = raw.get("data", [])
    if not records:
        raise HubEauNoDataError(f"No water network found for commune {code_commune!r}")
    return str(records[0].get("nom_commune") or code_commune)


class QualiteEauConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow for ha_q_eau."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            code_commune = user_input[CONF_CODE_COMMUNE]
            session = async_get_clientsession(self.hass)
            client = HubEauClient(session)

            try:
                nom_commune = await _probe_commune(client, code_commune)
            except HubEauNoDataError:
                errors["base"] = "commune_not_found"
            except HubEauApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Hub'Eau probe")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(code_commune)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Qualité Eau {nom_commune} ({code_commune})",
                    data={
                        CONF_CODE_COMMUNE: code_commune,
                        CONF_NOM_COMMUNE: nom_commune,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_STEP_USER_SCHEMA,
            errors=errors,
            description_placeholders={
                "geo_api_url": "https://geo.api.gouv.fr/communes",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return QualiteEauOptionsFlow()


class QualiteEauOptionsFlow(OptionsFlow):
    """Options flow — polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    OPT_SCAN_INTERVAL_H,
                    default=options.get(OPT_SCAN_INTERVAL_H, DEFAULT_SCAN_INTERVAL_H),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=OPT_SCAN_INTERVAL_H_MIN, max=OPT_SCAN_INTERVAL_H_MAX),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
