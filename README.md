# LNG Cargo Diversion Decision Engine (Dash)
## What this solves
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
## Model (transparent, intentionally simple)
Netback is:
Revenue − VoyageCost − CarbonCost
Where:
- Revenue = DestinationPrice (USD/MMBtu) × DeliveredEnergy (MMBtu)
- DeliveredEnergy = (Cargo_m3 − BoilOff_m3) × 0.45 t/m3 × 52 MMBtu/t
- VoyageCost = FuelCost + TimeCharter + Canal + Port
- CarbonCost = FuelTonnes × CO2Factor × EUA_price

## How to run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py