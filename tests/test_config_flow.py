"""Tests for the QualiteEau config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ha_q_eau.const import CONF_CODE_COMMUNE, DOMAIN

from .conftest import MOCK_CODE_COMMUNE, MOCK_NOM_COMMUNE


@pytest.fixture(autouse=True)
def bypass_setup():
    """Bypass async_setup_entry to speed up config flow tests."""
    with patch(
        "custom_components.ha_q_eau.async_setup_entry",
        return_value=True,
    ):
        yield


class TestConfigFlowUser:
    async def test_user_step_shows_form(self, hass):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    async def test_user_step_success(self, hass):
        """Config flow creates entry with correct data when commune is valid.

        Uses hass.config_entries directly to inspect the created entry without
        triggering async_setup_entry (which spawns a _run_safe_shutdown_loop
        thread that the pytest-homeassistant-custom-component verify_cleanup
        fixture cannot handle in version 0.13.x).
        """
        with patch(
            "custom_components.ha_q_eau.config_flow._probe_commune",
            return_value=MOCK_NOM_COMMUNE,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_USER},
                data={CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE},
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_CODE_COMMUNE] == MOCK_CODE_COMMUNE
        assert MOCK_NOM_COMMUNE in result["title"]
        # Verify the entry was registered in config_entries
        entries = hass.config_entries.async_entries(DOMAIN)
        assert len(entries) == 1
        assert entries[0].unique_id == MOCK_CODE_COMMUNE
    async def test_user_step_commune_not_found(self, hass):
        from custom_components.ha_q_eau.api.exceptions import HubEauNoDataError

        with patch(
            "custom_components.ha_q_eau.config_flow._probe_commune",
            side_effect=HubEauNoDataError("not found"),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_USER},
                data={CONF_CODE_COMMUNE: "99999"},
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "commune_not_found"

    async def test_user_step_cannot_connect(self, hass):
        from custom_components.ha_q_eau.api.exceptions import HubEauApiError

        with patch(
            "custom_components.ha_q_eau.config_flow._probe_commune",
            side_effect=HubEauApiError(503),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_USER},
                data={CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE},
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"

    async def test_user_step_already_configured(self, hass):
        with patch(
            "custom_components.ha_q_eau.config_flow._probe_commune",
            return_value=MOCK_NOM_COMMUNE,
        ):
            # First setup
            await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_USER},
                data={CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE},
            )
            # Second setup — same commune
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_USER},
                data={CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE},
            )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"
