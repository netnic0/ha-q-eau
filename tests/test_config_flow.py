"""Tests for the QualiteEau config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ha_q_eau.api.exceptions import HubEauApiError, HubEauNoDataError
from custom_components.ha_q_eau.config_flow import _probe_commune
from custom_components.ha_q_eau.const import (
    CONF_CODE_COMMUNE,
    CONF_NOM_COMMUNE,
    DOMAIN,
)

from .conftest import (
    MOCK_CODE_COMMUNE,
    MOCK_COMMUNE_UDI_RESPONSE,
    MOCK_LATEST_RESULT_RESPONSE,
    MOCK_NOM_COMMUNE,
    MOCK_PARAMS_RESPONSE,
)


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


class TestUserFlow:
    """End-to-end tests for async_step_user using the hass fixture.

    These cover Silver tier `config-flow-test-coverage`: the full flow including
    form display, schema validation, API probing, error mapping, and entry
    creation is exercised — not just the inner _probe_commune helper.
    """

    async def _start_form(self, hass: HomeAssistant):
        """Open the user step and return the initial form result."""
        return await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    async def test_form_is_shown_initially(self, hass: HomeAssistant):
        result = await self._start_form(hass)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    async def test_successful_submission_creates_entry(self, hass: HomeAssistant):
        """Happy path: valid INSEE → probe succeeds → entry created."""
        await self._start_form(hass)

        with patch(
            "custom_components.ha_q_eau.config_flow.HubEauClient",
            return_value=MagicMock(
                async_get_communes_udi=AsyncMock(
                    return_value=MOCK_COMMUNE_UDI_RESPONSE
                )
            ),
        ), patch(
            # Block the actual integration setup that follows entry creation —
            # we are testing the flow only, not the runtime.
            "custom_components.ha_q_eau.async_setup_entry",
            return_value=True,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_USER},
                data={CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE},
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == {
            CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE,
            CONF_NOM_COMMUNE: MOCK_NOM_COMMUNE,
        }
        assert MOCK_NOM_COMMUNE in result["title"]
        assert MOCK_CODE_COMMUNE in result["title"]

    async def test_no_data_error_maps_to_commune_not_found(
        self, hass: HomeAssistant
    ):
        """Probe raises HubEauNoDataError → form re-shown with 'commune_not_found'."""
        with patch(
            "custom_components.ha_q_eau.config_flow.HubEauClient",
            return_value=MagicMock(
                async_get_communes_udi=AsyncMock(
                    side_effect=HubEauNoDataError("no UDI")
                )
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_USER},
                data={CONF_CODE_COMMUNE: "99999"},
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "commune_not_found"}

    async def test_api_error_maps_to_cannot_connect(self, hass: HomeAssistant):
        """Probe raises HubEauApiError → form re-shown with 'cannot_connect'."""
        with patch(
            "custom_components.ha_q_eau.config_flow.HubEauClient",
            return_value=MagicMock(
                async_get_communes_udi=AsyncMock(side_effect=HubEauApiError(503))
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_USER},
                data={CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE},
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}

    async def test_already_configured_aborts(self, hass: HomeAssistant):
        """Adding a commune already configured → flow aborts with 'already_configured'."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        existing = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE,
                CONF_NOM_COMMUNE: MOCK_NOM_COMMUNE,
            },
            unique_id=MOCK_CODE_COMMUNE,
        )
        existing.add_to_hass(hass)

        with patch(
            "custom_components.ha_q_eau.config_flow.HubEauClient",
            return_value=MagicMock(
                async_get_communes_udi=AsyncMock(
                    return_value=MOCK_COMMUNE_UDI_RESPONSE
                )
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_USER},
                data={CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE},
            )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    async def test_invalid_insee_format_rejected_by_schema(
        self, hass: HomeAssistant
    ):
        """Schema-level validation: non-5-digit INSEE codes raise vol.Invalid.

        The voluptuous Match regex `^\\d{5}$` runs before the API probe, so the
        flow should NOT call the Hub'Eau API at all for malformed inputs.
        """
        import voluptuous as vol

        with pytest.raises(vol.Invalid):
            await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_USER},
                data={CONF_CODE_COMMUNE: "abcde"},  # not 5 digits
            )
