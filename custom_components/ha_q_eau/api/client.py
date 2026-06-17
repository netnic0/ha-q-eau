"""Async HTTP client for the Hub'Eau qualite_eau_potable API.

No authentication required — the API is fully public (open data).

Endpoints used:
  GET /communes_udi         — maps commune → UDI network codes (static, cached at setup)
  GET /resultats_dis        — individual sample results with conformity conclusions

Rate limits: not documented; monthly data refresh. Daily polling is sufficient.
INSEE commune codes (5 digits) are the primary identifier, not postal codes.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .exceptions import HubEauApiError, HubEauNoDataError

_LOGGER = logging.getLogger(__name__)

_BASE_URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable"
_COMMUNES_UDI_ENDPOINT = "/communes_udi"
_RESULTATS_DIS_ENDPOINT = "/resultats_dis"

_DEFAULT_PAGE_SIZE = 200


class HubEauClient:
    """Async Hub'Eau qualite_eau_potable client — one instance per config entry."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """GET an endpoint and return parsed JSON.

        Hub'Eau returns HTTP 206 (Partial Content) when paginating with size < total count.
        Both 200 and 206 carry valid JSON bodies and must be accepted.
        """
        url = f"{_BASE_URL}{endpoint}"
        async with self._session.get(url, params=params) as resp:
            if resp.status not in (200, 206):
                raise HubEauApiError(resp.status, await resp.text())
            data: Any = await resp.json(content_type=None)
        if data is None:
            raise HubEauNoDataError(f"Empty response from {endpoint}")
        return data

    async def async_get_communes_udi(self, code_commune: str) -> dict[str, Any]:
        """GET /communes_udi for a given INSEE commune code.

        Returns raw paginated Hub'Eau response:
          { "count": N, "data": [ { "code_commune", "nom_commune",
            "code_reseau", "nom_reseau", ... } ] }
        """
        params: dict[str, Any] = {
            "code_commune": code_commune,
            "size": _DEFAULT_PAGE_SIZE,
        }
        data = await self._get(_COMMUNES_UDI_ENDPOINT, params)
        if not isinstance(data, dict):
            raise HubEauNoDataError(f"Expected dict from communes_udi, got {type(data)}")
        return data

    async def async_get_latest_result(self, code_commune: str) -> dict[str, Any]:
        """GET the most recent sample conformity result for a commune.

        Returns the latest record from resultats_dis sorted desc by date.
        """
        params: dict[str, Any] = {
            "code_commune": code_commune,
            "size": 1,
            "sort": "desc",
            "fields": (
                "code_commune,nom_commune,nom_distributeur,code_departement,"
                "date_prelevement,conformite_limites_bact_prelevement,"
                "conformite_limites_pc_prelevement,conclusion_conformite_prelevement,"
                "reseaux"
            ),
        }
        data = await self._get(_RESULTATS_DIS_ENDPOINT, params)
        if not isinstance(data, dict):
            raise HubEauNoDataError(f"Expected dict from resultats_dis, got {type(data)}")
        if not data.get("data"):
            raise HubEauNoDataError(f"No water quality results for commune {code_commune}")
        return data

    async def async_get_recent_parameters(
        self,
        code_commune: str,
        date_min: str | None = None,
    ) -> dict[str, Any]:
        """GET recent individual parameter readings for a commune.

        date_min: ISO date string (YYYY-MM-DD). Defaults to 90 days ago if None.
        """
        params: dict[str, Any] = {
            "code_commune": code_commune,
            "size": _DEFAULT_PAGE_SIZE,
            "sort": "desc",
            "fields": (
                "code_parametre,libelle_parametre,resultat_numerique,"
                "resultat_alphanumerique,libelle_unite,limite_qualite_parametre,"
                "date_prelevement"
            ),
        }
        if date_min:
            params["date_min_prelevement"] = f"{date_min} 00:00:00"
        data = await self._get(_RESULTATS_DIS_ENDPOINT, params)
        if not isinstance(data, dict):
            raise HubEauNoDataError(f"Expected dict from resultats_dis (params), got {type(data)}")
        return data

    async def async_validate_commune(self, code_commune: str) -> bool:
        """Return True if the INSEE code has at least one UDI record.

        Used during config flow validation.
        """
        try:
            result = await self.async_get_communes_udi(code_commune)
            return int(result.get("count", 0)) > 0
        except (HubEauApiError, HubEauNoDataError):
            return False
