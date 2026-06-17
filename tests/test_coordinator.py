"""Tests for the QualiteEauCoordinator parsers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.ha_q_eau.api.exceptions import HubEauNoDataError
from custom_components.ha_q_eau.coordinator import (
    _parse_communes_udi,
    _parse_latest_result,
    _parse_parameters,
)
from custom_components.ha_q_eau.const import PARAM_NITRATES, PARAM_PH

from .conftest import (
    MOCK_CODE_COMMUNE,
    MOCK_COMMUNE_UDI_RESPONSE,
    MOCK_LATEST_RESULT_RESPONSE,
    MOCK_PARAMS_RESPONSE,
)

NOW = datetime(2026, 6, 17, 12, 0, 0, tzinfo=UTC)


class TestParseCommunes:
    def test_parse_udi_extracts_commune_info(self):
        result = _parse_communes_udi(MOCK_CODE_COMMUNE, MOCK_COMMUNE_UDI_RESPONSE)
        assert result.nom_commune == "PARIS"
        assert result.code_departement == "75"
        assert "075000221" in result.reseaux
        assert "075000222" in result.reseaux

    def test_parse_udi_deduplicates_reseaux(self):
        raw = {
            "data": [
                {"code_commune": "75056", "nom_commune": "PARIS", "code_departement": "75", "code_reseau": "AAA"},
                {"code_commune": "75056", "nom_commune": "PARIS", "code_departement": "75", "code_reseau": "AAA"},
            ]
        }
        result = _parse_communes_udi("75056", raw)
        assert result.reseaux.count("AAA") == 1

    def test_parse_udi_empty_returns_fallback(self):
        result = _parse_communes_udi("75056", {"data": []})
        assert result.code_commune == "75056"
        assert result.nom_commune == "75056"


class TestParseLatestResult:
    def test_parse_latest_result_success(self):
        result = _parse_latest_result(MOCK_LATEST_RESULT_RESPONSE, NOW)
        assert result.conformite_bact == "C"
        assert result.conformite_pc == "C"
        assert result.nom_distributeur == "EAU DE PARIS"
        assert result.conclusion == "Eau conforme aux exigences de qualité."

    def test_parse_latest_result_invalid_date_fallback(self):
        raw = {
            "data": [{
                "code_commune": "75056",
                "nom_commune": "PARIS",
                "nom_distributeur": "EAU DE PARIS",
                "date_prelevement": "not-a-date",
                "conformite_limites_bact_prelevement": "C",
                "conformite_limites_pc_prelevement": "C",
                "conclusion_conformite_prelevement": "",
            }]
        }
        result = _parse_latest_result(raw, NOW)
        assert result.date_prelevement == NOW

    def test_parse_latest_result_empty_raises(self):
        with pytest.raises(HubEauNoDataError):
            _parse_latest_result({"data": []}, NOW)


class TestParseParameters:
    def test_parse_parameters_extracts_tracked(self):
        result = _parse_parameters(MOCK_PARAMS_RESPONSE)
        codes = {p.code_parametre for p in result}
        assert PARAM_NITRATES in codes
        assert PARAM_PH in codes

    def test_parse_parameters_deduplicates_per_code(self):
        raw = {
            "data": [
                {
                    "code_parametre": PARAM_NITRATES,
                    "libelle_parametre": "Nitrates",
                    "resultat_numerique": 10.0,
                    "resultat_alphanumerique": "10",
                    "libelle_unite": "mg/L",
                    "limite_qualite_parametre": "<=50",
                    "date_prelevement": "2026-04-30T10:00:00",
                },
                {
                    "code_parametre": PARAM_NITRATES,
                    "libelle_parametre": "Nitrates",
                    "resultat_numerique": 8.0,
                    "resultat_alphanumerique": "8",
                    "libelle_unite": "mg/L",
                    "limite_qualite_parametre": "<=50",
                    "date_prelevement": "2026-03-15T10:00:00",
                },
            ]
        }
        result = _parse_parameters(raw)
        nitrates = [p for p in result if p.code_parametre == PARAM_NITRATES]
        assert len(nitrates) == 1
        assert nitrates[0].resultat_numerique == 10.0

    def test_parse_parameters_ignores_untracked(self):
        raw = {
            "data": [
                {
                    "code_parametre": "9999",
                    "libelle_parametre": "Unknown param",
                    "resultat_numerique": 1.0,
                    "resultat_alphanumerique": "1",
                    "libelle_unite": "units",
                    "limite_qualite_parametre": "",
                    "date_prelevement": "2026-04-30T10:00:00",
                }
            ]
        }
        result = _parse_parameters(raw)
        assert len(result) == 0

    def test_parse_parameters_handles_null_numeric(self):
        raw = {
            "data": [
                {
                    "code_parametre": PARAM_NITRATES,
                    "libelle_parametre": "Nitrates",
                    "resultat_numerique": None,
                    "resultat_alphanumerique": "<ld",
                    "libelle_unite": "mg/L",
                    "limite_qualite_parametre": "<=50",
                    "date_prelevement": "2026-04-30T10:00:00",
                }
            ]
        }
        result = _parse_parameters(raw)
        assert result[0].resultat_numerique is None
        assert result[0].resultat_alphanumerique == "<ld"
