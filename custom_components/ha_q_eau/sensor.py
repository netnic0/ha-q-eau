"""Sensor platform for the ha_q_eau integration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime

from .const import (
    CONFORMITY_CODE_COMPLIANT,
    CONFORMITY_CODE_NON_COMPLIANT,
    DOMAIN,
    TRACKED_PARAMS,
)
from .entity import QualiteEauEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import QualiteEauCoordinator

PARALLEL_UPDATES = 0

CONFORMITY_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="conformity_bact",
        translation_key="conformity_bact",
        device_class=SensorDeviceClass.ENUM,
        options=["C", "N", "D", "S"],
    ),
    SensorEntityDescription(
        key="conformity_pc",
        translation_key="conformity_pc",
        device_class=SensorDeviceClass.ENUM,
        options=["C", "N", "D", "S"],
    ),
    SensorEntityDescription(
        key="sample_date",
        translation_key="sample_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="data_age_hours",
        translation_key="data_age_hours",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="distributor",
        translation_key="distributor",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

_PARAM_SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    tracked_key: SensorEntityDescription(
        key=f"param_{tracked_key}",
        translation_key=f"param_{tracked_key}",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    )
    for tracked_key in TRACKED_PARAMS.values()
}


class QualiteEauConformitySensor(QualiteEauEntity, SensorEntity):
    """Sensor for conformity/diagnostic fields."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: QualiteEauCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, translation_key=description.translation_key or description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | datetime | float | None:
        data = self.coordinator.data
        if data is None:
            return None
        key = self.entity_description.key
        reading = data.latest_reading
        now = datetime.now(UTC)

        if key == "conformity_bact":
            return reading.conformite_bact
        if key == "conformity_pc":
            return reading.conformite_pc
        if key == "sample_date":
            return reading.date_prelevement
        if key == "data_age_hours":
            delta = now - reading.fetched_at
            return round(delta.total_seconds() / 3600, 1)
        if key == "distributor":
            return reading.nom_distributeur or data.commune_info.nom_distributeur
        return None

    @property
    def icon(self) -> str | None:
        key = self.entity_description.key
        if key not in ("conformity_bact", "conformity_pc"):
            return None
        data = self.coordinator.data
        if data is None:
            return "mdi:water-off"
        val = (
            data.latest_reading.conformite_bact
            if key == "conformity_bact"
            else data.latest_reading.conformite_pc
        )
        if val == CONFORMITY_CODE_COMPLIANT:
            return "mdi:water-check"
        if val == CONFORMITY_CODE_NON_COMPLIANT:
            return "mdi:water-alert"
        return "mdi:water-question"

    @property
    def extra_state_attributes(self) -> dict | None:
        data = self.coordinator.data
        if data is None:
            return None
        if self.entity_description.key in ("conformity_bact", "conformity_pc"):
            return {"conclusion": data.latest_reading.conclusion}
        return None


class QualiteEauParameterSensor(QualiteEauEntity, SensorEntity):
    """Sensor for a single tracked water quality parameter."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: QualiteEauCoordinator,
        description: SensorEntityDescription,
        code_parametre: str,
    ) -> None:
        super().__init__(coordinator, translation_key=description.translation_key or description.key)
        self.entity_description = description
        self._code_parametre = code_parametre

    def _find_reading(self):  # type: ignore[return]
        data = self.coordinator.data
        if data is None:
            return None
        for param in data.parameters:
            if param.code_parametre == self._code_parametre:
                return param
        return None

    @property
    def native_value(self) -> float | None:
        param = self._find_reading()
        return param.resultat_numerique if param else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        param = self._find_reading()
        return param.libelle_unite or None if param else None

    @property
    def extra_state_attributes(self) -> dict | None:
        param = self._find_reading()
        if param is None:
            return None
        return {
            "result_text": param.resultat_alphanumerique,
            "quality_limit": param.limite_qualite,
            "sample_date": param.date_prelevement.isoformat(),
            "parameter_name": param.libelle_parametre,
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register sensor entities for a config entry."""
    coordinator: QualiteEauCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        QualiteEauConformitySensor(coordinator, desc) for desc in CONFORMITY_SENSORS
    ]
    for code_parametre, tracked_key in TRACKED_PARAMS.items():
        desc = _PARAM_SENSOR_DESCRIPTIONS[tracked_key]
        entities.append(QualiteEauParameterSensor(coordinator, desc, code_parametre))

    async_add_entities(entities)
