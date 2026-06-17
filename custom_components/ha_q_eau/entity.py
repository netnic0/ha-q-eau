"""Base entity class for ha_q_eau entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CODE_COMMUNE, DOMAIN

if TYPE_CHECKING:
    from .coordinator import QualiteEauCoordinator


class QualiteEauEntity(CoordinatorEntity["QualiteEauCoordinator"]):
    """Base class for all ha_q_eau entities tied to a commune."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: "QualiteEauCoordinator",
        translation_key: str,
    ) -> None:
        super().__init__(coordinator)
        code_commune = coordinator.config_entry.data[CONF_CODE_COMMUNE]
        self._attr_unique_id = f"{code_commune}_{translation_key}"
        self._attr_translation_key = translation_key

        data = coordinator.data
        nom_commune = data.commune_info.nom_commune if data else code_commune
        nom_distributeur = (
            data.commune_info.nom_distributeur if data else ""
        ) or "Hub'Eau"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, code_commune)},
            name=f"Qualité Eau {nom_commune}",
            manufacturer=nom_distributeur,
            model="Hub'Eau qualite_eau_potable",
            configuration_url="https://hubeau.eaufrance.fr/page/api-qualite-eau-potable",
            suggested_area="Home",
        )
