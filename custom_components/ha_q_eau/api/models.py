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

    @property
    def parameters_by_code(self) -> Mapping[str, ParameterReading]:
        """Return parameters indexed by their Sandre code.

        Used by sensor entities for O(1) lookup instead of repeatedly
        scanning the parameters tuple (was 24 linear scans per render
        cycle with 8 parameter sensors × 3 properties each).

        Wrapped in MappingProxyType to keep the snapshot conceptually
        immutable in line with the frozen dataclass.
        """
        return MappingProxyType({p.code_parametre: p for p in self.parameters})
