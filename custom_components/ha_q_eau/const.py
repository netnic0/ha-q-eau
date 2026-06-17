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

# ── Repair issue identifiers ─────────────────────────────────────────────────
ISSUE_STALE_DATA: Final[str] = "stale_data"

# ── Water quality conformity codes ───────────────────────────────────────────
CONFORMITY_CODE_COMPLIANT: Final[str] = "C"
CONFORMITY_CODE_NON_COMPLIANT: Final[str] = "N"
CONFORMITY_CODE_INSUFFICIENT: Final[str] = "D"
CONFORMITY_CODE_NOT_APPLICABLE: Final[str] = "S"

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
