"""Tests for the sensor entities (Silver tier)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.ha_q_eau.const import (
    CONF_CODE_COMMUNE,
    CONF_NOM_COMMUNE,
    DOMAIN,
    PARAM_NITRATES,
    PARAM_PH,
)
from custom_components.ha_q_eau.coordinator import QualiteEauCoordinator
from custom_components.ha_q_eau.sensor import (
    QualiteEauConformitySensor,
    QualiteEauParameterSensor,
    CONFORMITY_SENSORS,
    _PARAM_SENSOR_DESCRIPTIONS,
)

from .conftest import (
    MOCK_CODE_COMMUNE,
    MOCK_NOM_COMMUNE,
    mock_water_quality_data,
)


@pytest.fixture
def mock_coordinator(hass: HomeAssistant, mock_water_quality_data):
    """Return a coordinator with mocked data."""
    from unittest.mock import MagicMock
    from homeassistant.config_entries import ConfigEntry

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
        desc = next(d for d in CONFORMITY_SENSORS if d.key == "conformity_bact")
        sensor = QualiteEauConformitySensor(mock_coordinator, desc)
        assert sensor.native_value == "compliant"

    def test_conformity_pc_value(self, mock_coordinator):
        desc = next(d for d in CONFORMITY_SENSORS if d.key == "conformity_pc")
        sensor = QualiteEauConformitySensor(mock_coordinator, desc)
        assert sensor.native_value == "compliant"

    def test_conformity_bact_icon_compliant(self, mock_coordinator):
        desc = next(d for d in CONFORMITY_SENSORS if d.key == "conformity_bact")
        sensor = QualiteEauConformitySensor(mock_coordinator, desc)
        assert sensor.icon == "mdi:water-check"

    def test_conformity_bact_icon_non_compliant(self, mock_coordinator, mock_water_quality_data):
        from custom_components.ha_q_eau.api.models import WaterQualityReading, WaterQualityData
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
        )
        desc = next(d for d in CONFORMITY_SENSORS if d.key == "conformity_bact")
        sensor = QualiteEauConformitySensor(mock_coordinator, desc)
        assert sensor.icon == "mdi:water-alert"

    def test_conformity_extra_attributes_include_conclusion(self, mock_coordinator):
        desc = next(d for d in CONFORMITY_SENSORS if d.key == "conformity_bact")
        sensor = QualiteEauConformitySensor(mock_coordinator, desc)
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "conclusion" in attrs
        assert "conforme" in attrs["conclusion"].lower()

    def test_sample_date_returns_datetime(self, mock_coordinator):
        desc = next(d for d in CONFORMITY_SENSORS if d.key == "sample_date")
        sensor = QualiteEauConformitySensor(mock_coordinator, desc)
        assert isinstance(sensor.native_value, datetime)

    def test_data_age_hours_returns_float(self, mock_coordinator):
        desc = next(d for d in CONFORMITY_SENSORS if d.key == "data_age_hours")
        sensor = QualiteEauConformitySensor(mock_coordinator, desc)
        val = sensor.native_value
        assert isinstance(val, float)
        assert val >= 0

    def test_distributor_returns_string(self, mock_coordinator):
        desc = next(d for d in CONFORMITY_SENSORS if d.key == "distributor")
        sensor = QualiteEauConformitySensor(mock_coordinator, desc)
        assert sensor.native_value == "EAU DE PARIS"

    def test_unique_id_includes_commune_and_key(self, mock_coordinator):
        desc = next(d for d in CONFORMITY_SENSORS if d.key == "conformity_bact")
        sensor = QualiteEauConformitySensor(mock_coordinator, desc)
        assert MOCK_CODE_COMMUNE in sensor.unique_id
        assert "conformity_bact" in sensor.unique_id

    def test_no_data_returns_none(self, mock_coordinator):
        mock_coordinator.data = None
        desc = next(d for d in CONFORMITY_SENSORS if d.key == "conformity_bact")
        sensor = QualiteEauConformitySensor(mock_coordinator, desc)
        assert sensor.native_value is None


class TestParameterSensor:
    def test_nitrates_value(self, mock_coordinator):
        desc = _PARAM_SENSOR_DESCRIPTIONS["nitrates"]
        sensor = QualiteEauParameterSensor(mock_coordinator, desc, PARAM_NITRATES)
        assert sensor.native_value == 12.5

    def test_ph_value(self, mock_coordinator):
        desc = _PARAM_SENSOR_DESCRIPTIONS["ph"]
        sensor = QualiteEauParameterSensor(mock_coordinator, desc, PARAM_PH)
        assert sensor.native_value == 7.4

    def test_unit_of_measurement_from_api(self, mock_coordinator):
        desc = _PARAM_SENSOR_DESCRIPTIONS["nitrates"]
        sensor = QualiteEauParameterSensor(mock_coordinator, desc, PARAM_NITRATES)
        assert sensor.native_unit_of_measurement == "mg/L"

    def test_extra_attributes_include_limit(self, mock_coordinator):
        desc = _PARAM_SENSOR_DESCRIPTIONS["nitrates"]
        sensor = QualiteEauParameterSensor(mock_coordinator, desc, PARAM_NITRATES)
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "quality_limit" in attrs
        assert "50" in attrs["quality_limit"]

    def test_missing_parameter_returns_none(self, mock_coordinator):
        from custom_components.ha_q_eau.const import PARAM_FLUORIDE
        desc = _PARAM_SENSOR_DESCRIPTIONS["fluoride"]
        sensor = QualiteEauParameterSensor(mock_coordinator, desc, PARAM_FLUORIDE)
        # Fluoride not in mock data
        assert sensor.native_value is None
        assert sensor.native_unit_of_measurement is None
        assert sensor.extra_state_attributes is None

    def test_no_data_returns_none(self, mock_coordinator):
        mock_coordinator.data = None
        desc = _PARAM_SENSOR_DESCRIPTIONS["nitrates"]
        sensor = QualiteEauParameterSensor(mock_coordinator, desc, PARAM_NITRATES)
        assert sensor.native_value is None
