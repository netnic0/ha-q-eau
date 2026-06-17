# Qualité Eau Potable (France)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/netnic0/ha-q-eau.svg)](https://github.com/netnic0/ha-q-eau/releases)
[![License](https://img.shields.io/github/license/netnic0/ha-q-eau.svg)](LICENSE)

Home Assistant custom integration for **French drinking water quality** — powered by the open-data [Hub'Eau qualite_eau_potable API](https://hubeau.eaufrance.fr/page/api-qualite-eau-potable) (no account, no API key required).

Monitor your tap water conformity (bacteriological + physico-chemical) and individual parameters (nitrates, pH, turbidity, E. coli, chlorine, hardness, fluoride…) directly in Home Assistant.

---

## Features

- **Global conformity sensors** — bacteriological and physico-chemical conformity with human-readable labels (Conforme / Non conforme / Données insuffisantes)
- **Individual parameter sensors** — nitrates, pH, turbidity, E. coli, enterococcus, residual chlorine, hardness (TH), fluoride
- **Dynamic icons** — green droplet ✅ when compliant, red alert 🚨 when non-compliant
- **Diagnostic sensors** — sample date, data age in hours, distributor name
- **Multi-commune** — add as many communes as needed, each gets its own HA device
- **Configurable polling interval** — default 24h (Hub'Eau data refreshes monthly)
- **No authentication** — Hub'Eau is 100% open data

---

## Requirements

- Home Assistant 2024.1.0 or later
- [HACS](https://hacs.xyz/) installed

---

## Installation

### Via HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/netnic0/ha-q-eau` with category **Integration**
3. Search for "Qualité Eau Potable" and install
4. Restart Home Assistant

### Manual

1. Copy `custom_components/ha_q_eau/` to your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Qualité Eau Potable**
3. Enter your **INSEE commune code** (5 digits)

> **Finding your INSEE code:** Your postal code ≠ INSEE code.  
> Look it up at https://geo.api.gouv.fr/communes?codePostal=XXXXX  
> Example: Paris = `75056`, Lyon 1er = `69123`

---

## Entities

For each configured commune, the following sensors are created:

| Entity | Description | Unit |
|--------|-------------|------|
| `conformity_bact` | Bacteriological conformity | Enum |
| `conformity_pc` | Physico-chemical conformity | Enum |
| `param_nitrates` | Nitrates | mg/L |
| `param_ph` | pH | unit pH |
| `param_turbidity` | Turbidity | NFU |
| `param_ecoli` | Escherichia coli | n/(100mL) |
| `param_enterococcus` | Enterococcus | n/(100mL) |
| `param_chlorine` | Residual chlorine | mg/L |
| `param_hardness` | Hardness (TH) | °F |
| `param_fluoride` | Fluoride | mg/L |
| `sample_date` | Date of last sample | Timestamp |
| `data_age_hours` | Hours since last fetch | h |
| `distributor` | Water distributor name | — |

---

## Lovelace dashboard

An example dashboard is provided in [`lovelace_examples/water_quality_dashboard.yaml`](lovelace_examples/water_quality_dashboard.yaml).

Replace `YOUR_COMMUNE_CODE` with your INSEE code in the file, then paste it as a new dashboard view.

**Required HACS frontend cards:**
- [mushroom](https://github.com/piitaya/lovelace-mushroom) (recommended)

---

## Data source

All data comes from the French government open-data API:

- **Hub'Eau qualite_eau_potable** — https://hubeau.eaufrance.fr/page/api-qualite-eau-potable
- Data is published monthly by the French Ministry of Health (Ministère chargé de la santé)
- Coverage: all French communes with a regulated public water supply

---

## Limitations

- Data is updated **monthly** — this integration is not suitable for real-time monitoring
- Not all parameters are available for all communes (rural areas may have fewer analyses)
- Historical data is available but not yet exposed — only the most recent sample per parameter is shown
- DOM-TOM coverage may be incomplete in the Hub'Eau API

---

## Contributing

Issues and PRs welcome at https://github.com/netnic0/ha-q-eau

---

## License

MIT
