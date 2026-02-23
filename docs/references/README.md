# Reference Documentation

This folder contains screenshots and excerpts from official sources used in the LNG Cargo Diversion Engine.

## IMO MEPC.308(73) - CO₂ Emission Factors

**Source:** [IMO Resolution MEPC.308(73)](https://wwwcdn.imo.org/localresources/en/OurWork/Environment/Documents/Air%20pollution/MEPC.308(73).pdf)

**Title:** 2018 Guidelines on the Method of Calculation of the Attained Energy Efficiency Design Index (EEDI) for New Ships

**Relevant Data Used:**
- **VLSFO (Very Low Sulfur Fuel Oil):** 3.114 tCO₂/tonne fuel
- **LNG (Liquefied Natural Gas):** 2.75 tCO₂/tonne fuel

These emission factors are used in `data/carbon_params.csv` for calculating carbon costs in the netback model.

**Citation:**
> International Maritime Organization (IMO). "2018 Guidelines on the Method of Calculation of the Attained Energy Efficiency Design Index (EEDI) for New Ships." Resolution MEPC.308(73), adopted 26 October 2018.

---

## Screenshots

Screenshots from the IMO MEPC.308(73) document showing the emission factor tables used in this project.

### Files:
- `imo_screenshot_1.png` - CO₂ emission factors table
- `imo_screenshot_2.png` - Additional reference data

---

## Usage in Project

These emission factors are applied in:
- `engine/netback.py` - Carbon cost calculations
- `data/carbon_params.csv` - Static parameters
- EU ETS compliance cost modeling

---

*Note: All referenced materials are publicly available regulatory documents from the International Maritime Organization.*
