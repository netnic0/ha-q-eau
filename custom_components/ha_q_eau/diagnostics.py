"""Diagnostics support for ha_q_eau (Silver tier requirement).

Implements the `async_get_config_entry_diagnostics` hook so users can download
an anonymized YAML dump of the integration state (`Settings → Devices & Services
→ ha_q_eau → ⋮ → Download diagnostics`) when filing a bug report.

No PII redaction is performed: every field originates from the public Hub'Eau
open-data API (commune name, INSEE code, distributor name, parameter values).
The user's HA instance does not contribute any private data to this dump.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import QualiteEauConfigEntry, QualiteEauCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: QualiteEauConfigEntry
) -> dict[str, Any]:
    """Return a JSON-serialisable dump of the entry + coordinator state.

    `entry.runtime_data` is set by `async_setup_entry`; for an unloaded or
    pre-setup entry HA leaves the attribute as the sentinel `UNDEFINED`.
    `getattr(..., None)` collapses the sentinel to `None` so the diagnostics
    dump degrades gracefully and remains JSON-serialisable.
    """
    coordinator: QualiteEauCoordinator | None = getattr(entry, "runtime_data", None)

    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "minor_version": getattr(entry, "minor_version", None),
            "data": dict(entry.data),
            "options": dict(entry.options),
            "unique_id": entry.unique_id,
        },
        "coordinator": {
            "last_update_success": (
                coordinator.last_update_success if coordinator else None
            ),
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator and coordinator.update_interval
                else None
            ),
            "data": _dump_data(coordinator),
        },
    }


def _dump_data(coordinator: QualiteEauCoordinator | None) -> dict[str, Any] | None:
    """Convert the frozen WaterQualityData snapshot into a plain dict.

    `dataclasses.asdict` recursively expands nested frozen dataclasses
    (CommuneInfo, WaterQualityReading, ParameterReading) into JSON-friendly
    structures. Datetime values are serialised via `default=str` to handle
    `date_prelevement` / `fetched_at` cleanly. The `parameters_by_code`
    MappingProxyType is dropped — it is redundant with `parameters` and
    `asdict` does not handle MappingProxyType natively.
    """
    if coordinator is None or coordinator.data is None:
        return None

    snapshot = coordinator.data
    return {
        "commune_info": _dataclass_to_jsonable(snapshot.commune_info),
        "latest_reading": _dataclass_to_jsonable(snapshot.latest_reading),
        "parameters": [_dataclass_to_jsonable(p) for p in snapshot.parameters],
    }


def _dataclass_to_jsonable(obj: Any) -> dict[str, Any]:
    """asdict + stringify any datetime values for JSON serialisation.

    Note: this is one-level only — it does NOT recurse into list/tuple
    container values. The current data models have no `list[datetime]`
    or `tuple[datetime, ...]` fields, so this is safe today. If the model
    evolves to nest datetimes inside containers, this helper must be
    upgraded to recursive descent.
    """
    raw = asdict(obj)
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in raw.items()}
