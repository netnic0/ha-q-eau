"""Sensor platform for the ha_q_eau integration.

All sensors are instances of a single :class:`QualiteEauSensor` class. The per-sensor
behaviour (value computation, icon resolution, dynamic unit, attribute mapping) is
expressed declaratively on a custom :class:`QualiteEauSensorDescription`. This removes
the if/elif key-dispatch chains that earlier lived in two specialised entity classes
and makes each sensor independently configurable from its description tuple alone.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime

from .api.models import WaterQualityData
from .const import (
    CONFORMITY_CODE_COMPLIANT,
    CONFORMITY_CODE_NON_COMPLIANT,
    DOMAIN,
    PARAM_UNITS,
    TRACKED_PARAMS,
)
from .entity import QualiteEauEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import QualiteEauCoordinator

PARALLEL_UPDATES = 0


# ── Description type ────────────────────────────────────────────────────────


def _none_value_fn(_: WaterQualityData, __: str | None) -> Any:
    """Default value_fn used when a description forgets to set one."""
    return None


@dataclass(frozen=True, kw_only=True)
class QualiteEauSensorDescription(SensorEntityDescription):
    """Sensor description carrying its own value/icon/attributes/unit logic.

    The callables receive the full :class:`WaterQualityData` snapshot plus the
    description's optional ``code_parametre`` so a single class can serve both
    aggregate sensors (conformity, distributor) and per-parameter sensors.
    """

    code_parametre: str | None = None
    """Sandre parameter code; only set for per-parameter sensors."""

    value_fn: Callable[[WaterQualityData, str | None], Any] = _none_value_fn
    """Compute the sensor's native_value from the coordinator snapshot."""

    icon_fn: Callable[[WaterQualityData, str | None], str | None] | None = None
    """Optional dynamic icon. When None, the description's static icon is used."""

    attrs_fn: Callable[[WaterQualityData, str | None], dict[str, Any] | None] | None = (
        None
    )
    """Optional extra_state_attributes producer."""

    dynamic_unit_fn: Callable[[WaterQualityData, str | None], str | None] | None = None
    """Optional unit override. Result takes precedence over native_unit_of_measurement
    when not None — used to surface the API-provided unit when present, falling back
    to the static canonical unit otherwise."""


# ── Value / icon / attribute helpers ────────────────────────────────────────


def _value_conformity_bact(d: WaterQualityData, _: str | None) -> str:
    return d.latest_reading.conformite_bact


def _value_conformity_pc(d: WaterQualityData, _: str | None) -> str:
    return d.latest_reading.conformite_pc


def _value_sample_date(d: WaterQualityData, _: str | None) -> datetime:
    return d.latest_reading.date_prelevement


def _value_data_age_hours(d: WaterQualityData, _: str | None) -> float:
    """Hours since the coordinator last fetched data from Hub'Eau.

    Note: this is the *fetch* age (poll cadence), not the age of the underlying
    water sample. The translation label has been clarified accordingly.
    """
    delta = datetime.now(UTC) - d.latest_reading.fetched_at
    return round(delta.total_seconds() / 3600, 1)


def _value_distributor(d: WaterQualityData, _: str | None) -> str:
    """Return the water distributor name with the same fallback chain as the device.

    `entity.py` falls back to "Hub'Eau" when both reading and commune_info are
    empty. The sensor state must agree with the device manufacturer to avoid
    UI inconsistency for small communes whose Hub'Eau record has no distributor.
    """
    return (
        d.latest_reading.nom_distributeur
        or d.commune_info.nom_distributeur
        or "Hub'Eau"
    )


def _icon_conformity(d: WaterQualityData, key: str | None) -> str:
    val = (
        d.latest_reading.conformite_bact
        if key == "conformity_bact"
        else d.latest_reading.conformite_pc
    )
    if val == CONFORMITY_CODE_COMPLIANT:
        return "mdi:water-check"
    if val == CONFORMITY_CODE_NON_COMPLIANT:
        return "mdi:water-alert"
    return "mdi:water-question"


def _attrs_conformity(d: WaterQualityData, _: str | None) -> dict[str, Any]:
    return {"conclusion": d.latest_reading.conclusion}


# ── Per-parameter helpers ───────────────────────────────────────────────────


def _value_parameter(d: WaterQualityData, code: str | None) -> float | None:
    if code is None:
        return None
    param = d.parameters_by_code.get(code)
    return param.resultat_numerique if param else None


def _unit_parameter(d: WaterQualityData, code: str | None) -> str | None:
    """Return the API-provided unit when present, else fall back to canonical.

    Hybrid strategy: preserve Hub'Eau's exact label when it sends one (avoids HA
    long-term-statistics unit-mismatch warnings if labels are stable), but fall
    back to a project-defined canonical when the API returns an empty string.
    """
    if code is None:
        return None
    param = d.parameters_by_code.get(code)
    if param and param.libelle_unite:
        return param.libelle_unite
    return PARAM_UNITS.get(code) if code else None


def _attrs_parameter(d: WaterQualityData, code: str | None) -> dict[str, Any] | None:
    if code is None:
        return None
    param = d.parameters_by_code.get(code)
    if param is None:
        return None
    return {
        "result_text": param.resultat_alphanumerique,
        "quality_limit": param.limite_qualite,
        "sample_date": param.date_prelevement.isoformat(),
        "parameter_name": param.libelle_parametre,
    }


# ── Description tuples ──────────────────────────────────────────────────────


_CONFORMITY_OPTIONS = [
    "compliant",
    "non_compliant",
    "insufficient_data",
    "not_applicable",
]


CONFORMITY_SENSORS: tuple[QualiteEauSensorDescription, ...] = (
    QualiteEauSensorDescription(
        key="conformity_bact",
        translation_key="conformity_bact",
        device_class=SensorDeviceClass.ENUM,
        options=_CONFORMITY_OPTIONS,
        value_fn=_value_conformity_bact,
        icon_fn=_icon_conformity,
        attrs_fn=_attrs_conformity,
    ),
    QualiteEauSensorDescription(
        key="conformity_pc",
        translation_key="conformity_pc",
        device_class=SensorDeviceClass.ENUM,
        options=_CONFORMITY_OPTIONS,
        value_fn=_value_conformity_pc,
        icon_fn=_icon_conformity,
        attrs_fn=_attrs_conformity,
    ),
    QualiteEauSensorDescription(
        key="sample_date",
        translation_key="sample_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_value_sample_date,
    ),
    QualiteEauSensorDescription(
        key="data_age_hours",
        translation_key="data_age_hours",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        value_fn=_value_data_age_hours,
    ),
    QualiteEauSensorDescription(
        key="distributor",
        translation_key="distributor",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_value_distributor,
    ),
)


def _build_param_descriptions() -> tuple[QualiteEauSensorDescription, ...]:
    """Build one sensor description per tracked parameter.

    The static native_unit_of_measurement comes from PARAM_UNITS (canonical units),
    while dynamic_unit_fn lets the API value win when present (cf. _unit_parameter).
    """
    return tuple(
        QualiteEauSensorDescription(
            key=f"param_{tracked_key}",
            translation_key=f"param_{tracked_key}",
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
            native_unit_of_measurement=PARAM_UNITS.get(code),
            code_parametre=code,
            value_fn=_value_parameter,
            attrs_fn=_attrs_parameter,
            dynamic_unit_fn=_unit_parameter,
        )
        for code, tracked_key in TRACKED_PARAMS.items()
    )


PARAM_SENSORS: tuple[QualiteEauSensorDescription, ...] = _build_param_descriptions()


# ── Entity ──────────────────────────────────────────────────────────────────


class QualiteEauSensor(QualiteEauEntity, SensorEntity):
    """Single entity class driven by :class:`QualiteEauSensorDescription`."""

    entity_description: QualiteEauSensorDescription

    def __init__(
        self,
        coordinator: QualiteEauCoordinator,
        description: QualiteEauSensorDescription,
    ) -> None:
        super().__init__(
            coordinator,
            translation_key=description.translation_key or description.key,
        )
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        if data is None:
            return None
        return self.entity_description.value_fn(
            data, self.entity_description.code_parametre
        )

    @property
    def icon(self) -> str | None:
        icon_fn = self.entity_description.icon_fn
        if icon_fn is None:
            return self.entity_description.icon
        data = self.coordinator.data
        if data is None:
            # Conformity sensors keep their fallback icon when data is absent.
            return "mdi:water-off"
        return icon_fn(data, self.entity_description.key)

    @property
    def native_unit_of_measurement(self) -> str | None:
        unit_fn = self.entity_description.dynamic_unit_fn
        if unit_fn is None:
            return self.entity_description.native_unit_of_measurement
        data = self.coordinator.data
        if data is None:
            # Fall back to the canonical static unit so HA statistics keep a stable unit
            # across coordinator outages instead of toggling None ↔ "mg/L".
            return self.entity_description.native_unit_of_measurement
        dynamic = unit_fn(data, self.entity_description.code_parametre)
        return dynamic if dynamic is not None else self.entity_description.native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        attrs_fn = self.entity_description.attrs_fn
        if attrs_fn is None:
            return None
        data = self.coordinator.data
        if data is None:
            return None
        return attrs_fn(data, self.entity_description.code_parametre)


# ── Backwards-compatible aliases ────────────────────────────────────────────
# Removed in this refactor: the old QualiteEauConformitySensor /
# QualiteEauParameterSensor classes had different constructor signatures than
# the unified QualiteEauSensor (the parameter class took a third positional
# `code_parametre` arg now stored on the description). Keeping them as bare
# aliases would silently raise TypeError on the old 3-arg call form. Callers
# (including tests) must migrate to QualiteEauSensor explicitly.


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register sensor entities for a config entry."""
    coordinator: QualiteEauCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        QualiteEauSensor(coordinator, desc) for desc in CONFORMITY_SENSORS
    ]
    entities.extend(QualiteEauSensor(coordinator, desc) for desc in PARAM_SENSORS)

    async_add_entities(entities)
