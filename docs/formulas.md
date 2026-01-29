# LNG Cargo Diversion Engine - Formula Reference

## Physical Constants

| Constant | Value | Unit | Source |
|----------|-------|------|--------|
| **LNG Density** | 0.45 | tonnes/m³ | Industry standard for LNG at -162°C |
| **Energy Content** | 52 | MMBtu/tonne | Higher Heating Value (HHV) for LNG |
| **CO₂ Factor** | 3.114 | tCO₂/tonne fuel | IMO emission factor for marine fuel |
| **Boil-off Rate** | 0.10 | %/day | Modern TFDE vessel standard |

## Vessel Specifications

| Parameter | Value | Unit | Notes |
|-----------|-------|------|-------|
| **Cargo Capacity** | 174,000 | m³ | Standard for large LNG carriers |
| **Laden Speed** | 19.5 | knots | Typical for TFDE vessels |
| **Fuel Consumption** | 130 | tonnes/day | At laden speed |
| **Ballast Speed** | 20.5 | knots | When empty |

## Route Distances

| Route | Distance | Unit | Notes |
|-------|----------|------|-------|
| **US Gulf → Rotterdam** | 5,000 | nm | Via Atlantic |
| **US Gulf → Tokyo** | 9,500 | nm | Via Panama Canal |

## Key Formulas

### 1. Voyage Time
```
Voyage Days = Distance (nautical miles) / (Speed (knots) × 24 hours)
```

**Example:**
- Europe: 5,000 nm / (19.5 kn × 24) = 10.7 days
- Asia: 9,500 nm / (19.5 kn × 24) = 20.3 days

---

### 2. Boil-Off Calculation
```
Boil-Off (m³) = Cargo Capacity (m³) × Boil-Off Rate (%/day) × Voyage Days / 100

Delivered Cargo (m³) = Cargo Capacity (m³) - Boil-Off (m³)

Delivered Energy (MMBtu) = Delivered Cargo (m³) × Density (t/m³) × Energy Content (MMBtu/t)
```

**Example (Asia):**
- Boil-off: 174,000 × 0.10% × 20.3 = 353 m³
- Delivered: 174,000 - 353 = 173,647 m³
- Energy: 173,647 × 0.45 × 52 = 4,062,378 MMBtu

---

### 3. Voyage Costs

#### Fuel Cost
```
Fuel Cost ($) = Fuel Consumption (t/day) × Voyage Days × Fuel Price ($/t)
```

#### Charter Cost
```
Charter Cost ($) = Freight Rate ($/day) × Voyage Days
```

#### Carbon Cost
```
Carbon Emissions (tCO₂) = Fuel Consumed (t) × CO₂ Factor (tCO₂/t)
Carbon Cost ($) = Carbon Emissions (tCO₂) × EUA Price ($/tCO₂)
```

#### Total Voyage Cost
```
Total Voyage Cost = Fuel Cost + Charter Cost + Carbon Cost
```

---

### 4. Netback Calculation
```
Revenue ($) = Price ($/MMBtu) × Delivered Energy (MMBtu)

Netback ($) = Revenue - Total Voyage Cost

Delta Netback ($) = Asia Netback - Europe Netback
```

**This is the raw profit opportunity from diverting to Asia.**

---

### 5. Decision Rule

#### Adjusted Delta Netback
```
Adjusted ΔNetback = (Raw ΔNetback × (1 - Basis Adjustment%)) - Operational Risk Buffer
```

Where:
- **Basis Adjustment**: 5% (accounts for basis risk in JKM/TTF correlation)
- **Operational Risk Buffer**: $250,000 (demurrage, delays, terminal issues)

#### Decision Threshold
```
IF Adjusted ΔNetback ≥ Decision Buffer ($500,000)
   THEN DIVERT
ELSE
   KEEP original route
```

---

### 6. Hedge Sizing

#### Calculate Hedge Volume
```
Hedge Energy (MMBtu) = Delivered Energy to Asia (MMBtu) × Coverage (%)

JKM Lots = floor(Hedge Energy / Lot Size)
TTF Lots = floor(Hedge Energy / Lot Size)
```

Where:
- **Coverage**: 80% (hedge 80% of cargo, leave 20% unhedged)
- **Lot Size**: 10,000 MMBtu (standard for JKM/TTF futures)

**Trade Ticket:**
- LONG JKM (buy Asia exposure)
- SHORT TTF (sell Europe exposure)

---

### 7. Stress Testing

Recalculate Adjusted ΔNetback under shocked scenarios:

| Scenario | JKM Shock | Freight Shock | EUA Shock |
|----------|-----------|---------------|-----------|
| **Spread Collapse** | -$0.50/MMBtu | - | - |
| **Spread Widen** | +$0.50/MMBtu | - | - |
| **Freight Spike** | - | +$10,000/day | - |
| **Freight Drop** | - | -$10,000/day | - |
| **Carbon Spike** | - | - | +$10/tCO₂ |
| **Combined Adverse** | -$0.50/MMBtu | +$10,000/day | +$10/tCO₂ |

Check if decision flips under stress.

---

## Data Sources

### Market Data (Daily Updates Required)
- **JKM/TTF Prices**: Platts, ICIS, Argus Media
- **Freight Rates**: Baltic Exchange, Spark Commodities
- **Fuel Prices**: Platts Bunkerworld, Ship & Bunker
- **EUA Prices**: ICE Futures Europe

### Static Data (Periodic Updates)
- **Vessel Specs**: Clarksons Research, IHS Markit
- **Route Distances**: Sea-web Distance Tables
- **Port Costs**: Port authorities, terminal operators

---

## Business Rules

### Decision Thresholds (Configurable)
- **Decision Buffer**: $500,000 (minimum profit to justify diversion)
- **Operational Risk Buffer**: $250,000 (covers unexpected costs)
- **Basis Adjustment**: 5% (conservative haircut for basis risk)

### Hedge Parameters
- **Coverage**: 80% (standard for physical hedging)
- **Lot Size**: 10,000 MMBtu (exchange-traded futures)

### Risk Parameters
- **Stress Spread**: ±$0.50/MMBtu (1 standard deviation)
- **Stress Freight**: ±$10,000/day (typical volatility)
- **Stress EUA**: ±$10/tCO₂ (regulatory risk)

---

## Assumptions & Limitations

### Assumptions
1. No ballast voyage costs included (assumes vessel already positioned)
2. Panama Canal transit time included in voyage days
3. Constant boil-off rate (doesn't vary with ambient temperature)
4. Linear fuel consumption (doesn't account for weather)
5. No port congestion or waiting time

### Limitations
1. Simplified voyage routing (no weather routing optimization)
2. Static EUA prices (doesn't forecast carbon costs)
3. No counterparty credit risk modeling
4. Assumes liquid JKM/TTF futures markets
5. No physical delivery constraints (assumes terminal capacity)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-28 | Initial documentation |

---

## References

1. International Maritime Organization (IMO) - GHG Emission Factors
2. International Group of Liquefied Natural Gas Importers (GIIGNL) - Industry Standards
3. Baltic Exchange - Freight Rate Methodology
4. ICE Futures Europe - Contract Specifications (JKM, TTF)
5. Clarksons Research - Vessel Specifications Database
