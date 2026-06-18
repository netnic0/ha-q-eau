"""DataUpdateCoordinator for the ha_q_eau integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HubEauApiError, HubEauClient, HubEauNoDataError
from .api.models import (
    CommuneInfo,
    ParameterReading,
    WaterQualityData,
    WaterQualityReading,
    make_parameters_by_code,
)
from .const import (
    CONF_CODE_COMMUNE,
    CONFORMITY_CODE_INSUFFICIENT,
    CONFORMITY_CODE_MAP,
    DEFAULT_SCAN_INTERVAL_H,
    DOMAIN,
    OPT_SCAN_INTERVAL_H,
    PARAM_LOOKBACK_DAYS,
    TRACKED_PARAMS,
)

_LOGGER = logging.getLogger(__name__)


class QualiteEauCoordinator(DataUpdateCoordinator[WaterQualityData]):
    """Fetch Hub'Eau water quality data on a configurable schedule."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: HubEauClient,
        entry: ConfigEntry,
    ) -> None:
        scan_interval_h = entry.options.get(OPT_SCAN_INTERVAL_H, DEFAULT_SCAN_INTERVAL_H)
        super().__init__(
            hass,
            _LOGGER,
            name=f"Qualité Eau ({entry.data[CONF_CODE_COMMUNE]})",
            update_interval=timedelta(hours=scan_interval_h),
            config_entry=entry,
            always_update=False,
        )
        self._client = client
        code_commune: str = entry.data[CONF_CODE_COMMUNE]
        self._commune_info = CommuneInfo(
            code_commune=code_commune,
            nom_commune=entry.data.get("nom_commune", code_commune),
            nom_distributeur="",
            code_departement=code_commune[:2],
        )

    async def async_setup(self) -> None:
        """Fetch static commune/UDI metadata once at integration setup.

        UDI metadata is non-critical: when it fails, the coordinator falls back to
        the seeded CommuneInfo from the config entry. We narrow the except clause
        to the known network/API failure modes so genuine bugs (e.g. parser
        TypeErrors) propagate and surface in CI/logs instead of being swallowed.
        """
        code_commune: str = self.config_entry.data[CONF_CODE_COMMUNE]
        try:
            raw_udi = await self._client.async_get_communes_udi(code_commune)
            self._commune_info = _parse_communes_udi(code_commune, raw_udi)
        except (
            HubEauApiError,
            HubEauNoDataError,
            aiohttp.ClientError,
            asyncio.TimeoutError,
        ) as err:
            _LOGGER.warning("Could not fetch UDI metadata for %s: %s", code_commune, err)

    async def _async_update_data(self) -> WaterQualityData:
        """Fetch latest water quality data from the Hub'Eau API."""
        code_commune: str = self.config_entry.data[CONF_CODE_COMMUNE]
        now = datetime.now(UTC)

        try:
            raw_latest = await self._client.async_get_latest_result(code_commune)
        except HubEauApiError as err:
            raise UpdateFailed(f"Hub'Eau API error: {err}") from err
        except HubEauNoDataError as err:
            raise UpdateFailed(f"Hub'Eau no data: {err}") from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Hub'Eau network error: {err}") from err

        latest_reading = _parse_latest_result(raw_latest, now)

        parameters: tuple[ParameterReading, ...] = ()
        date_min = (now - timedelta(days=PARAM_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        try:
            raw_params = await self._client.async_get_recent_parameters(
                code_commune, date_min=date_min
            )
            parameters = _parse_parameters(raw_params)
        except (
            HubEauApiError,
            HubEauNoDataError,
            aiohttp.ClientError,
            asyncio.TimeoutError,
        ) as err:
            # Parameter detail is best-effort: missing params should not fail the
            # whole coordinator update — conformity sensors still publish a value.
            _LOGGER.warning(
                "Could not fetch parameter details for %s: %s", code_commune, err
            )

        return WaterQualityData(
            commune_info=self._commune_info,
            latest_reading=latest_reading,
            parameters=parameters,
            parameters_by_code=make_parameters_by_code(parameters),
        )


# ── Parsers ───────────────────────────────────────────────────────────────────


def _parse_communes_udi(code_commune: str, raw: dict[str, Any]) -> CommuneInfo:
    """Parse GET /communes_udi response into CommuneInfo."""
    records: list[dict[str, Any]] = raw.get("data", [])
    if not records:
        return CommuneInfo(
            code_commune=code_commune,
            nom_commune=code_commune,
            nom_distributeur="",
            code_departement=code_commune[:2],
        )

    first = records[0]
    nom_commune = str(first.get("nom_commune") or code_commune)
    code_departement = str(first.get("code_departement") or code_commune[:2])

    reseaux_codes: list[str] = []
    seen: set[str] = set()
    for record in records:
        code_reseau = str(record.get("code_reseau") or "")
        if code_reseau and code_reseau not in seen:
            reseaux_codes.append(code_reseau)
            seen.add(code_reseau)

    return CommuneInfo(
        code_commune=code_commune,
        nom_commune=nom_commune,
        nom_distributeur="",
        code_departement=code_departement,
        reseaux=tuple(reseaux_codes),
    )


def _parse_latest_result(raw: dict[str, Any], fetched_at: datetime) -> WaterQualityReading:
    """Parse the first record from GET /resultats_dis response."""
    records: list[dict[str, Any]] = raw.get("data", [])
    if not records:
        raise HubEauNoDataError("Empty data array in resultats_dis response")

    record = records[0]

    raw_date = str(record.get("date_prelevement") or "")
    try:
        date_prelevement = datetime.fromisoformat(raw_date)
        # Ensure timezone-aware — Hub'Eau returns naive datetimes (local/UTC ambiguous).
        # HA requires timezone-aware datetimes for TIMESTAMP device class.
        if date_prelevement.tzinfo is None:
            date_prelevement = date_prelevement.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        date_prelevement = fetched_at

    return WaterQualityReading(
        code_commune=str(record.get("code_commune") or ""),
        nom_commune=str(record.get("nom_commune") or ""),
        nom_distributeur=str(record.get("nom_distributeur") or ""),
        date_prelevement=date_prelevement,
        conformite_bact=CONFORMITY_CODE_MAP.get(
            str(record.get("conformite_limites_bact_prelevement") or ""), CONFORMITY_CODE_INSUFFICIENT
        ),
        conformite_pc=CONFORMITY_CODE_MAP.get(
            str(record.get("conformite_limites_pc_prelevement") or ""), CONFORMITY_CODE_INSUFFICIENT
        ),
        conclusion=str(record.get("conclusion_conformite_prelevement") or ""),
        fetched_at=fetched_at,
    )


def _parse_parameters(raw: dict[str, Any]) -> tuple[ParameterReading, ...]:
    """Parse /resultats_dis records into ParameterReading objects.

    Keeps only the most recent reading per tracked parameter (response is sorted desc).
    """
    records: list[dict[str, Any]] = raw.get("data", [])
    seen_params: set[str] = set()
    result: list[ParameterReading] = []

    for record in records:
        code_parametre = str(record.get("code_parametre") or "")
        if code_parametre not in TRACKED_PARAMS:
            continue
        if code_parametre in seen_params:
            continue
        seen_params.add(code_parametre)

        raw_date = str(record.get("date_prelevement") or "")
        try:
            date_prelevement = datetime.fromisoformat(raw_date)
            # Ensure timezone-aware — Hub'Eau returns naive datetimes.
            # Mirror the pattern in _parse_latest_result to avoid mixing aware/naive
            # datetimes between conformity sensors and parameter sensors.
            if date_prelevement.tzinfo is None:
                date_prelevement = date_prelevement.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            _LOGGER.debug(
                "Skipping parameter %s: unparseable date %r", code_parametre, raw_date
            )
            continue

        raw_num = record.get("resultat_numerique")
        try:
            resultat_numerique: float | None = float(raw_num) if raw_num is not None else None
        except (TypeError, ValueError):
            resultat_numerique = None

        result.append(
            ParameterReading(
                code_parametre=code_parametre,
                libelle_parametre=str(record.get("libelle_parametre") or code_parametre),
                resultat_numerique=resultat_numerique,
                resultat_alphanumerique=str(record.get("resultat_alphanumerique") or ""),
                libelle_unite=str(record.get("libelle_unite") or ""),
                limite_qualite=str(record.get("limite_qualite_parametre") or ""),
                date_prelevement=date_prelevement,
            )
        )

    return tuple(result)
