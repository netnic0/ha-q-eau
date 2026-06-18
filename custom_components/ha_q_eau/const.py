"""Constants for the ha_q_eau Home Assistant integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final[str] = "ha_q_eau"

# ── Config entry keys ─────────────────────────────────────────────────────────
CONF_CODE_COMMUNE: Final[str] = "code_commune"
CONF_NOM_COMMUNE: Final[str] = "nom_commune"

# ── Options keys ──────────────────────────────────────────────────────────────
OPT_SCAN_INTERVAL_H: Final[str] = "scan_interval_h"

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_SCAN_INTERVAL_H: Final[int] = 24
"""Poll every 24 hours — Hub'Eau data is updated monthly."""

# ── Options bounds ────────────────────────────────────────────────────────────
OPT_SCAN_INTERVAL_H_MIN: Final[int] = 6
OPT_SCAN_INTERVAL_H_MAX: Final[int] = 168

# ── Coordinator: parameter history lookback ─────────────────────────────────
# Hub'Eau publishes monthly; 90 days covers the last few sample cycles, leaves
# enough room when a commune skips a month, and stays small enough that a single
# size=200 page returns everything for any French commune.
PARAM_LOOKBACK_DAYS: Final[int] = 90

# ── Water quality conformity codes ───────────────────────────────────────────
# Raw API values (C/N/D/S) are mapped to HA-compliant slugs via CONFORMITY_CODE_MAP.
CONFORMITY_CODE_COMPLIANT: Final[str] = "compliant"
CONFORMITY_CODE_NON_COMPLIANT: Final[str] = "non_compliant"
CONFORMITY_CODE_INSUFFICIENT: Final[str] = "insufficient_data"
CONFORMITY_CODE_NOT_APPLICABLE: Final[str] = "not_applicable"

CONFORMITY_CODE_MAP: Final[dict[str, str]] = {
    "C": CONFORMITY_CODE_COMPLIANT,
    "N": CONFORMITY_CODE_NON_COMPLIANT,
    "D": CONFORMITY_CODE_INSUFFICIENT,
    "S": CONFORMITY_CODE_NOT_APPLICABLE,
}

# ── Tracked parameter Sandre codes → sensor key ──────────────────────────────
# Only these parameters get dedicated sensor entities.
PARAM_NITRATES: Final[str] = "1340"
PARAM_TURBIDITY: Final[str] = "1301"
PARAM_PH: Final[str] = "1302"
PARAM_ECOLI: Final[str] = "1449"
PARAM_ENTEROCOCCUS: Final[str] = "1450"
PARAM_CHLORINE: Final[str] = "1332"
PARAM_HARDNESS: Final[str] = "1345"
PARAM_FLUORIDE: Final[str] = "1327"

TRACKED_PARAMS: Final[dict[str, str]] = {
    PARAM_NITRATES: "nitrates",
    PARAM_TURBIDITY: "turbidity",
    PARAM_PH: "ph",
    PARAM_ECOLI: "ecoli",
    PARAM_ENTEROCOCCUS: "enterococcus",
    PARAM_CHLORINE: "chlorine",
    PARAM_HARDNESS: "hardness",
    PARAM_FLUORIDE: "fluoride",
}

# ── Canonical units for tracked parameters ──────────────────────────────────
# Used as a fallback when the Hub'Eau API returns an empty libelle_unite.
# The API value (when present) takes precedence to avoid HA long-term-statistics
# unit-mismatch warnings if Hub'Eau ever changes its labels (e.g. "mg/l" → "mg/L").
# Codes that map to None are dimensionless (pH).
PARAM_UNITS: Final[dict[str, str | None]] = {
    PARAM_NITRATES: "mg/L",
    PARAM_TURBIDITY: "NFU",
    PARAM_PH: None,
    PARAM_ECOLI: "n/(100mL)",
    PARAM_ENTEROCOCCUS: "n/(100mL)",
    PARAM_CHLORINE: "mg/L",
    PARAM_HARDNESS: "°f",
    PARAM_FLUORIDE: "mg/L",
}
