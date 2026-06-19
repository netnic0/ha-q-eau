"""Tests for the sensor entities (Silver tier)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.ha_q_eau.const import (
    CONF_CODE_COMMUNE,
    CONF_NOM_COMMUNE,
    DOMAIN,
    PARAM_FLUORIDE,
    PARAM_NITRATES,
    PARAM_PH,
)
from custom_components.ha_q_eau.coordinator import QualiteEauCoordinator
from custom_components.ha_q_eau.sensor import (
    CONFORMITY_SENSORS,
    PARAM_SENSORS,
    QualiteEauSensor,
)

from .conftest import (
    MOCK_CODE_COMMUNE,
    MOCK_NOM_COMMUNE,
    mock_water_quality_data,
)


def _desc_by_key(descriptions, key: str):
    """Find a SensorEntityDescription by its key."""
    return next(d for d in descriptions if d.key == key)


def _param_desc(code_parametre: str):
    """Find a parameter description by its Sandre code."""
    return next(d for d in PARAM_SENSORS if d.code_parametre == code_parametre)


@pytest.fixture
def mock_coordinator(hass: HomeAssistant, mock_water_quality_data):
    """Return a coordinator with mocked data."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.domain = DOMAIN
    entry.data = {CONF_CODE_COMMUNE: MOCK_CODE_COMMUNE, CONF_NOM_COMMUNE: MOCK_NOM_COMMUNE}
    entry.options = {}

    coord = MagicMock(spec=QualiteEauCoordinator)
    coord.data = mock_water_quality_data
    coord.config_entry = entry
    coord.async_add_listener = MagicMock(return_value=lambda: None)
    return coord


class TestConformitySensor:
    def test_conformity_bact_value(self, mock_coordinator):
        sensor = QualiteEauSensor(mock_coordinator, _desc_by_key(CONFORMITY_SENSORS, "conformity_bact"))
        assert sensor.native_value == "compliant"

    def test_conformity_pc_value(self, mock_coordinator):
        sensor = QualiteEauSensor(mock_coordinator, _desc_by_key(CONFORMITY_SENSORS, "conformity_pc"))
        assert sensor.native_value == "compliant"

    def test_conformity_bact_icon_compliant(self, mock_coordinator):
        sensor = QualiteEauSensor(mock_coordinator, _desc_by_key(CONFORMITY_SENSORS, "conformity_bact"))
        assert sensor.icon == "mdi:water-check"

    def test_conformity_bact_icon_non_compliant(self, mock_coordinator, mock_water_quality_data):
        from custom_components.ha_q_eau.api.models import (
            WaterQualityData,
            WaterQualityReading,
            make_parameters_by_code,
        )
        now = datetime(2026, 6, 17, 12, 0, 0, tzinfo=UTC)
        bad_reading = WaterQualityReading(
            code_commune=MOCK_CODE_COMMUNE,
            nom_commune=MOCK_NOM_COMMUNE,
            nom_distributeur="EAU DE PARIS",
            date_prelevement=now,
            conformite_bact="non_compliant",
            conformite_pc="compliant",
            conclusion="Non conforme.",
            fetched_at=now,
        )
        mock_coordinator.data = WaterQualityData(
            commune_info=mock_water_quality_data.commune_info,
            latest_reading=bad_reading,
            parameters=mock_water_quality_data.parameters,
            parameters_by_code=make_parameters_by_code(mock_water_quality_data.parameters),
        )
        sensor = QualiteEauSensor(mock_coordinator, _desc_by_key(CONFORMITY_SENSORS, "conformity_bact"))
        assert sensor.icon == "mdi:water-alert"

    def test_conformity_extra_attributes_include_conclusion(self, mock_coordinator):
        sensor = QualiteEauSensor(mock_coordinator, _desc_by_key(CONFORMITY_SENSORS, "conformity_bact"))
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "conclusion" in attrs
        assert "conforme" in attrs["conclusion"].lower()

    def test_sample_date_returns_datetime(self, mock_coordinator):
        sensor = QualiteEauSensor(mock_coordinator, _desc_by_key(CONFORMITY_SENSORS, "sample_date"))
        assert isinstance(sensor.native_value, datetime)

    def test_data_age_hours_returns_float(self, mock_coordinator):
        """Pin "now" so the test asserts the exact computed value, not just type.

        mock_water_quality_data sets fetched_at = 2026-06-17T12:00 UTC. Setting
        a frozen now of 14:30 UTC gives an exact expected age of 2.5 hours.
        """
        frozen_now = datetime(2026, 6, 17, 14, 30, 0, tzinfo=UTC)

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):  # type: ignore[override]
                return frozen_now if tz is None else frozen_now.astimezone(tz)

        with patch("custom_components.ha_q_eau.sensor.datetime", _FrozenDatetime):
            sensor = QualiteEauSensor(mock_coordinator, _desc_by_key(CONFORMITY_SENSORS, "data_age_hours"))
            val = sensor.native_value

        assert val == 2.5

    def test_distributor_returns_string(self, mock_coordinator):
        sensor = QualiteEauSensor(mock_coordinator, _desc_by_key(CONFORMITY_SENSORS, "distributor"))
        assert sensor.native_value == "EAU DE PARIS"

    def test_unique_id_includes_commune_and_key(self, mock_coordinator):
        sensor = QualiteEauSensor(mock_coordinator, _desc_by_key(CONFORMITY_SENSORS, "conformity_bact"))
        assert MOCK_CODE_COMMUNE in sensor.unique_id
        assert "conformity_bact" in sensor.unique_id

    def test_no_data_returns_none(self, mock_coordinator):
        mock_coordinator.data = None
        sensor = QualiteEauSensor(mock_coordinator, _desc_by_key(CONFORMITY_SENSORS, "conformity_bact"))
        assert sensor.native_value is None


class TestParameterSensor:
    def test_nitrates_value(self, mock_coordinator):
        sensor = QualiteEauSensor(mock_coordinator, _param_desc(PARAM_NITRATES))
        assert sensor.native_value == 12.5

    def test_ph_value(self, mock_coordinator):
        sensor = QualiteEauSensor(mock_coordinator, _param_desc(PARAM_PH))
        assert sensor.native_value == 7.4

    def test_unit_of_measurement_from_api(self, mock_coordinator):
        """API value wins over canonical fallback when present."""
        sensor = QualiteEauSensor(mock_coordinator, _param_desc(PARAM_NITRATES))
        assert sensor.native_unit_of_measurement == "mg/L"

    def test_unit_falls_back_to_canonical_when_param_absent(self, mock_coordinator):
        """When the parameter has no reading, the canonical static unit is returned.

        This is the hybrid fallback: keeps the unit stable across coordinator outages
        so HA long-term statistics do not flip None ↔ unit and trigger warnings.
        """
        sensor = QualiteEauSensor(mock_coordinator, _param_desc(PARAM_FLUORIDE))
        # Fluoride is canonical "mg/L" even though it is not present in the mock data.
        assert sensor.native_unit_of_measurement == "mg/L"

    def test_unit_falls_back_when_libelle_unite_empty(self, mock_coordinator, mock_water_quality_data):
        """Path B of the hybrid: param IS present but its libelle_unite is empty.

        Hub'Eau occasionally returns parameters with no unit string; the canonical
        PARAM_UNITS fallback must still kick in to keep HA statistics stable.
        """
        from custom_components.ha_q_eau.api.models import (
            ParameterReading,
            WaterQualityData,
            make_parameters_by_code,
        )
        # Replace the nitrates reading with one that has an empty libelle_unite.
        nitrates_no_unit = ParameterReading(
            code_parametre=PARAM_NITRATES,
            libelle_parametre="Nitrates",
            resultat_numerique=12.5,
            resultat_alphanumerique="12.5",
            libelle_unite="",  # ← empty unit, exercise canonical fallback
            limite_qualite="<=50 mg/L",
            date_prelevement=datetime(2026, 4, 30, 10, 0, tzinfo=UTC),
        )
        params = (nitrates_no_unit,) + tuple(
            p for p in mock_water_quality_data.parameters if p.code_parametre != PARAM_NITRATES
        )
        mock_coordinator.data = WaterQualityData(
            commune_info=mock_water_quality_data.commune_info,
            latest_reading=mock_water_quality_data.latest_reading,
            parameters=params,
            parameters_by_code=make_parameters_by_code(params),
        )
        sensor = QualiteEauSensor(mock_coordinator, _param_desc(PARAM_NITRATES))
        assert sensor.native_unit_of_measurement == "mg/L"

    def test_extra_attributes_include_limit(self, mock_coordinator):
        sensor = QualiteEauSensor(mock_coordinator, _param_desc(PARAM_NITRATES))
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "quality_limit" in attrs
        assert "50" in attrs["quality_limit"]

    def test_missing_parameter_value_is_none(self, mock_coordinator):
        """Value is None when the parameter has no reading; attrs are None too."""
        sensor = QualiteEauSensor(mock_coordinator, _param_desc(PARAM_FLUORIDE))
        assert sensor.native_value is None
        assert sensor.extra_state_attributes is None

    def test_no_data_returns_none(self, mock_coordinator):
        mock_coordinator.data = None
        sensor = QualiteEauSensor(mock_coordinator, _param_desc(PARAM_NITRATES))
        assert sensor.native_value is None
