# LNG Cargo Diversion Decision Engine (Dash)
## Desk decision supported
Given today’s market conditions, should an LNG cargo be discharged in Europe or diverted to Asia — and if diverted, what is the hedge, size, and risk?
This is a trade decision engine:
- compute Europe netback vs Asia netback
- compute ΔNetback (Asia − Europe)
- apply conservative adjustments (basis adjustment + operational risk buffer)
- trigger a decision rule with a clear threshold
- generate a trade ticket (hedge legs + sizing)
- produce a stress pack and backtest
## Decision rule
Let:
- ΔNetback_raw = Netback_Asia − Netback_Europe
- ΔNetback_adj = ΔNetback_raw × (1 − BasisAdjustment) − OperationalRiskBuffer
**Rule:** Divert to Asia when ΔNetback_adj ≥ DecisionBuffer.
Otherwise, keep Europe discharge plan.
## Inputs (daily)
Market data (CSV):
- JKM and TTF prices (USD/MMBtu)
- LNG freight rates (USD/day) for vessel class (TFDE/MEGI)
- Fuel price (LNG / VLSFO) (USD/tonne)
- Carbon price (EUA, USD/tCO2)
Static / semi-static:
- Route distance (nautical miles)
- Vessel parameters: capacity (m3), speed (kn), fuel consumption (t/day), boil-off (%/day)
- Emission factors for fuels
Configuration (tunable):
- DecisionBuffer (USD)
- OperationalRiskBuffer (USD)
- Basis Adjustment (%)
- Hedge coverage (% of cargo energy)
- Lot sizes (MMBtu per lot)
- Stress shocks: spread, freight, EUA
## Outputs
For each evaluation date:
- Netback_Europe (USD)
- Netback_Asia (USD)
- ΔNetback_raw and ΔNetback_adj (USD)
- Trade decision (Divert / Keep)
- Trade ticket:
 - hedge legs (e.g., Long JKM / Short TTF)
 - hedge size in lots (coverage-based)
 - saved to /reports with timestamp
- Risk pack:
 - P&L impact under spread/freight/EUA shocks
- Backtest (simple):
 - number of triggered trades
 - hit-rate (trigger frequency)
 - average uplift (USD per triggered trade)
 - max drawdown (USD)
 - equity curve
## Model 
Netback is:
Revenue − VoyageCost − CarbonCost
Where:
- Revenue = DestinationPrice (USD/MMBtu) × DeliveredEnergy (MMBtu)
- DeliveredEnergy = (Cargo_m3 − BoilOff_m3) × 0.45 t/m3 × 52 MMBtu/t
- VoyageCost = FuelCost + TimeCharter + Canal + Port
- CarbonCost = FuelTonnes × CO2Factor × EUA_price
- Operational uncertainty (laycan slippage, terminal delays, demurrage) is handled via a fixed OperationalRiskBuffer rather than explici scheduling optimisation.
## Acceptance Criteria 
- Produces a clear divert / do-not-divert decision for a given date.
- Outputs a hedgeable trade ticket with explicit sizing
- Quantifies downside under spread, freight, and carbon shocks.
- Runs end-to-end in seconds using daily inputs.

## Data contracts (CSV schemas + units)
### 1) Market data (daily)
**data/benchmark_prices.csv**
- date (YYYY-MM-DD)
- TTF (USD/MMBtu)
- JKM (USD/MMBtu)
**data/freight_rates.csv**
- date (YYYY-MM-DD)
- TFDE_USD_day (USD/day)
- MEGI_USD_day (USD/day)
**data/fuel_prices.csv**
- date (YYYY-MM-DD)
- VLSFO_USD_per_t (USD/tonne)
- LNG_USD_per_t (USD/tonne)
### 2) Static / semi-static
**data/routes.csv**
- load_port (string)
- discharge_port (string)
- distance_nm (nautical miles)
**data/vessels.csv**
- vessel_class (TFDE|MEGI)
- cargo_capacity_m3 (m3)
- laden_speed_kn (knots)
- ballast_speed_kn (knots)
- boil_off_pct_per_day (% per day)
- fuel_consumption_tpd_laden (tonnes/day)
- fuel_consumption_tpd_ballast (tonnes/day)
**data/carbon_params.csv**
- param (string)
- value (float)
Required params:
- EUA_price_USD_per_t (USD/tCO2)
- CO2_factor_VLSFO_tCO2_per_t_fuel (tCO2 per tonne fuel)
- CO2_factor_LNG_tCO2_per_t_fuel (tCO2 per tonne fuel)
### 3) Config (tunable)
**data/config.csv**
- param (string)
- value (float)
Required params:
- DECISION_BUFFER_USD (USD)
- OPERATIONAL_RISK_BUFFER_USD (USD)
- BASIS_ADJUSTMENT_PCT (0–1)
- COVERAGE_PCT (0–1)
- JKM_LOT_MMBTU (MMBtu per lot)
- TTF_LOT_MMBTU (MMBtu per lot)
- STRESS_SPREAD_USD (USD/MMBtu)
- STRESS_FREIGHT_USD_PER_DAY (USD/day)
- STRESS_EUA_USD (USD/tCO2)

## Unit conventions 
- Prices: USD/MMBtu (JKM, TTF)
- Freight: USD/day
- Fuel: USD/tonne (LNG and VLSFO)
- Carbon: USD/tCO2
- Distance: nautical miles
- Speed: knots
- Consumption: tonnes/day
- Boil-off: % of cargo per day
- Cargo conversion constants used:
 - LNG density approx = 0.45 tonne per m3
 - Energy content approx = 52 MMBtu per tonne LNG

 ## Checks 
- All daily CSVs must have consistent dates and no duplicates
- No negative prices, freight rates, distances, or speeds
- BASIS_ADJUSTMENT_PCT and COVERAGE_PCT must be between 0 and 1
- vessel_class in vessels.csv must match TFDE/MEGI used in freight_rates.csv
- routes.csv must include the selected (load_port, discharge_port) pair

## How to run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py