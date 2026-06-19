"""Immutable data models for Hub'Eau qualite_eau_potable API responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class CommuneInfo:
    """Static metadata for the configured commune."""

    code_commune: str
    """INSEE commune code (5 digits, e.g. '75056')."""

    nom_commune: str
    """Commune name (e.g. 'PARIS')."""

    nom_distributeur: str
    """Water distributor name (e.g. 'EAU DE PARIS')."""

    code_departement: str
    """Department code (e.g. '75')."""

    reseaux: tuple[str, ...] = field(default_factory=tuple)
    """UDI (Unité de Distribution) network codes for this commune."""


@dataclass(frozen=True, slots=True)
class WaterQualityReading:
    """Latest water quality conformity conclusion for the commune."""

    code_commune: str
    nom_commune: str
    nom_distributeur: str

    date_prelevement: datetime
    """Timestamp of the sample collection."""

    conformite_bact: str
    """Bacterial conformity: C=Conforme, N=Non-conforme, D=Données insuffisantes, S=Sans objet."""

    conformite_pc: str
    """Physico-chemical conformity: same codes as conformite_bact."""

    conclusion: str
    """Human-readable conformity conclusion text."""

    fetched_at: datetime
    """Timestamp when this reading was retrieved from the API."""


@dataclass(frozen=True, slots=True)
class ParameterReading:
    """A single water quality parameter measurement."""

    code_parametre: str
    libelle_parametre: str
    """Human-readable parameter name (e.g. 'Nitrates', 'Escherichia coli /100ml - MF')."""

    resultat_numerique: float | None
    resultat_alphanumerique: str
    """Alphanumeric result string (e.g. '<1', '0.05')."""

    libelle_unite: str
    """Unit label (e.g. 'mg/L', 'n/(100mL)')."""

    limite_qualite: str
    """Regulatory quality limit (e.g. '<=50 mg/L')."""

    date_prelevement: datetime


@dataclass(frozen=True, slots=True)
class WaterQualityData:
    """Full coordinator snapshot for one commune."""

    commune_info: CommuneInfo
    latest_reading: WaterQualityReading
    parameters: tuple[ParameterReading, ...] = field(default_factory=tuple)
    """Recent individual parameter readings (last sample per parameter)."""

    parameters_by_code: Mapping[str, ParameterReading] = field(
        default_factory=lambda: MappingProxyType({})
    )
    """Parameters indexed by their Sandre code for O(1) sensor lookup.

    Populated once per coordinator update from `parameters` (via
    `make_parameters_by_code` below). Pre-computing here — instead of as
    a @property recomputed at every sensor render — avoids rebuilding the
    dict on every `native_value` / `native_unit_of_measurement` /
    `extra_state_attributes` call (was 24 dict allocations per render
    cycle with 8 parameter sensors × 3 properties each).
    """


def make_parameters_by_code(
    parameters: tuple[ParameterReading, ...],
) -> Mapping[str, ParameterReading]:
    """Build an immutable code→reading lookup from a parameters tuple.

    Helper used by the coordinator to populate `WaterQualityData.parameters_by_code`
    once per refresh. MappingProxyType keeps the snapshot conceptually immutable
    in line with the frozen dataclass.
    """
    return MappingProxyType({p.code_parametre: p for p in parameters})
