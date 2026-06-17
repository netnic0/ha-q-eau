"""Shared pytest fixtures for ha_q_eau tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ha_q_eau.api.models import (
    CommuneInfo,
    ParameterReading,
    WaterQualityData,
    WaterQualityReading,
)
from custom_components.ha_q_eau.const import (
    CONF_CODE_COMMUNE,
    CONF_NOM_COMMUNE,
    DOMAIN,
    PARAM_ECOLI,
    PARAM_NITRATES,
    PARAM_PH,
    PARAM_TURBIDITY,
)

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom integrations."""
    yield


MOCK_CODE_COMMUNE = "75056"
MOCK_NOM_COMMUNE = "PARIS"

MOCK_COMMUNE_UDI_RESPONSE = {
    "count": 2,
    "data": [
        {
            "code_commune": "75056",
            "nom_commune": "PARIS",
            "code_departement": "75",
            "code_reseau": "075000221",
            "nom_reseau": "CENTRE",
        },
        {
            "code_commune": "75056",
            "nom_commune": "PARIS",
            "code_departement": "75",
            "code_reseau": "075000222",
            "nom_reseau": "EST",
        },
    ],
}

MOCK_LATEST_RESULT_RESPONSE = {
    "count": 1,
    "data": [
        {
            "code_commune": "75056",
            "nom_commune": "PARIS",
            "nom_distributeur": "EAU DE PARIS",
            "code_departement": "75",
            "date_prelevement": "2026-04-30T10:00:00",
            "conformite_limites_bact_prelevement": "C",
            "conformite_limites_pc_prelevement": "C",
            "conclusion_conformite_prelevement": "Eau conforme aux exigences de qualité.",
            "reseaux": [{"code": "075000221", "nom": "CENTRE"}],
        }
    ],
}

MOCK_PARAMS_RESPONSE = {
    "count": 4,
    "data": [
        {
            "code_parametre": PARAM_NITRATES,
            "libelle_parametre": "Nitrates",
            "resultat_numerique": 12.5,
            "resultat_alphanumerique": "12.5",
            "libelle_unite": "mg/L",
            "limite_qualite_parametre": "<=50 mg/L",
            "date_prelevement": "2026-04-30T10:00:00",
        },
        {
            "code_parametre": PARAM_PH,
            "libelle_parametre": "pH",
            "resultat_numerique": 7.4,
            "resultat_alphanumerique": "7.4",
            "libelle_unite": "unité pH",
            "limite_qualite_parametre": "6.5-9 unité pH",
            "date_prelevement": "2026-04-30T10:00:00",
        },
        {
            "code_parametre": PARAM_TURBIDITY,
            "libelle_parametre": "Turbidité",
            "resultat_numerique": 0.3,
            "resultat_alphanumerique": "0.3",
            "libelle_unite": "NFU",
            "limite_qualite_parametre": "<=1 NFU",
            "date_prelevement": "2026-04-30T10:00:00",
        },
        {
            "code_parametre": PARAM_ECOLI,
            "libelle_parametre": "Escherichia coli /100ml - MF",
            "resultat_numerique": 0.0,
            "resultat_alphanumerique": "<1",
            "libelle_unite": "n/(100mL)",
            "limite_qualite_parametre": "<=0 n/(100mL)",
            "date_prelevement": "2026-04-30T10:00:00",
        },
    ],
}


@pytest.fixture
def mock_api_client():
    """Return a mocked HubEauClient."""
    with patch(
        "custom_components.ha_q_eau.api.client.HubEauClient"
    ) as mock_class:
        client = mock_class.return_value
        client.async_get_communes_udi = AsyncMock(return_value=MOCK_COMMUNE_UDI_RESPONSE)
        client.async_get_latest_result = AsyncMock(return_value=MOCK_LATEST_RESULT_RESPONSE)
        client.async_get_recent_parameters = AsyncMock(return_value=MOCK_PARAMS_RESPONSE)
        client.async_validate_commune = AsyncMock(return_value=True)
        yield client


@pytest.fixture
def mock_config_entry(hass):
    """Return a mock config entry."""
    from homeassistant.config_entries import ConfigEntry

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = {
        CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE,
        CONF_NOM_COMMUNE: MOCK_NOM_COMMUNE,
    }
    entry.options = {}
    entry.unique_id = MOCK_CODE_COMMUNE
    return entry


@pytest.fixture
def mock_water_quality_data() -> WaterQualityData:
    """Return a mock WaterQualityData snapshot."""
    now = datetime(2026, 6, 17, 12, 0, 0, tzinfo=UTC)
    commune_info = CommuneInfo(
        code_commune=MOCK_CODE_COMMUNE,
        nom_commune=MOCK_NOM_COMMUNE,
        nom_distributeur="EAU DE PARIS",
        code_departement="75",
        reseaux=("075000221", "075000222"),
    )
    reading = WaterQualityReading(
        code_commune=MOCK_CODE_COMMUNE,
        nom_commune=MOCK_NOM_COMMUNE,
        nom_distributeur="EAU DE PARIS",
        date_prelevement=datetime(2026, 4, 30, 10, 0, tzinfo=UTC),
        conformite_bact="C",
        conformite_pc="C",
        conclusion="Eau conforme aux exigences de qualité.",
        fetched_at=now,
    )
    params = (
        ParameterReading(
            code_parametre=PARAM_NITRATES,
            libelle_parametre="Nitrates",
            resultat_numerique=12.5,
            resultat_alphanumerique="12.5",
            libelle_unite="mg/L",
            limite_qualite="<=50 mg/L",
            date_prelevement=datetime(2026, 4, 30, 10, 0, tzinfo=UTC),
        ),
        ParameterReading(
            code_parametre=PARAM_PH,
            libelle_parametre="pH",
            resultat_numerique=7.4,
            resultat_alphanumerique="7.4",
            libelle_unite="unité pH",
            limite_qualite="6.5-9 unité pH",
            date_prelevement=datetime(2026, 4, 30, 10, 0, tzinfo=UTC),
        ),
    )
    return WaterQualityData(
        commune_info=commune_info,
        latest_reading=reading,
        parameters=params,
    )
