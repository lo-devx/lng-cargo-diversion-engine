# Glossary

A comprehensive reference of terms, acronyms, and concepts used in the LNG Cargo Diversion Decision Engine.

---

## Core Concepts

### **Netback**
The profit realized from selling LNG at a destination after subtracting all costs to get it there (voyage costs, fuel, carbon taxes, port fees). Think of it as "net proceeds after backing out all expenses."

**Formula**: `Netback = Revenue - Voyage Costs - Carbon Costs`

### **Uplift**
The additional profit gained by diverting a cargo from one destination to another. If Asia netback is $130M and Europe is $125M, the uplift is $5M.

- **Raw Uplift (Δ Raw)**: Simple difference between Asia and Europe netbacks
- **Adjusted Uplift (Δ Adj)**: Raw uplift minus basis haircut and operational buffer

### **DIVERT**
Decision to change the cargo's destination from Europe to Asia. Triggered when adjusted uplift exceeds the decision buffer threshold.

### **KEEP**
Decision to maintain the original Europe destination. Chosen when the Asia advantage is too small or negative after adjustments.

---

## Market Prices & Benchmarks

### **TTF (Title Transfer Facility)**
European natural gas price benchmark traded in the Netherlands. Represents the value of gas delivered to Europe. Currently sourced from Yahoo Finance (ticker: TTF=F).

### **JKM (Japan-Korea Marker)**
Asian LNG price benchmark representing spot LNG prices in Northeast Asia. Currently calculated as TTF + $2.75 premium (proxy until better data available).

### **EUA (European Union Allowance)**
Carbon emission allowances under the EU Emissions Trading System (EU ETS). Price per tonne of CO₂. Maritime shipping was included in EU ETS starting January 2024. Sourced from Yahoo Finance (ticker: CO2.L).

### **MMBtu**
Million British Thermal Units - standard unit for measuring natural gas energy content. LNG prices (TTF, JKM) are quoted in USD/MMBtu.

---

## Risk & Hedging

### **Hedge**
Financial trades used to lock in the price spread. If diverting to Asia, you hedge by buying JKM futures and selling TTF futures to protect against price movements during transit.

**Example**: BUY JKM 322 lots, SELL TTF 322 lots

### **Lot**
A standard contract size for futures trading. 
- TTF lot = 10,000 MMBtu
- JKM lot = 10,000 MMBtu

### **Coverage**
Percentage of the physical cargo energy hedged in the financial markets. Default 80% - leaves some exposure for basis adjustments and operational flexibility.

### **Basis Haircut**
Conservative discount applied to the price spread to account for basis risk (differences between physical prices and futures prices, timing mismatches, location differences). Default 5%.

### **Operational Buffer**
Fixed USD amount deducted from uplift to account for operational risks like port delays, weather, demurrage. Default $250,000.

### **Decision Buffer**
Minimum threshold uplift required to trigger DIVERT decision. Ensures the margin is meaningful enough to justify diversion costs and risks. Default $500,000.

---

## Shipping & Logistics

### **Freight Rate**
Daily cost to charter the LNG vessel, measured in USD/day. Includes time charter costs but not fuel. Varies by vessel class (TFDE, MEGI).

### **TFDE (Tri-Fuel Diesel Electric)**
LNG vessel propulsion system that can run on LNG, marine diesel, or LNG + diesel. Common modern vessel type.

### **MEGI (M-type Electronically Controlled Gas Injection)**
Advanced LNG vessel propulsion system with high fuel efficiency. More expensive but lower fuel consumption.

### **Boil-off**
Natural evaporation of LNG during voyage due to heat transfer. Measured as % of cargo per day (typically ~0.10-0.15% daily). Boil-off gas is used as fuel or reliquefied.

### **Cargo Capacity (m³)**
Vessel cargo tank volume in cubic meters. Standard large LNG carrier: 174,000 m³.

---

## Performance Metrics (Backtesting)

### **Hit Rate**
Percentage of days where DIVERT decision was triggered. Higher hit rate means more active strategy.

**Formula**: `Hit Rate = Triggered Trades / Total Observations`

**Example**: 530 triggers out of 530 days = 100% hit rate

### **Sharpe Ratio**
Risk-adjusted return metric. Measures average profit per unit of volatility. Higher is better. Values above 1.0 are considered good; above 2.0 is excellent.

**Formula**: `Sharpe = (Mean Return / Std Dev of Returns) × √252` (annualized)

**Example**: Sharpe of 439.74 indicates extremely consistent profits with low volatility

### **Max Drawdown**
Largest peak-to-trough decline in cumulative P&L. Measures worst-case loss scenario during the backtest period.

**Example**: $0 drawdown means cumulative P&L never decreased (no losing days)

### **Equity Curve**
Chart showing cumulative profit/loss over time. Upward slope indicates consistent profitability. Flat or declining sections show drawdown periods.

### **Total Uplift**
Sum of all adjusted uplifts from triggered DIVERT trades during the backtest period.

**Example**: $3.68 billion total uplift over 530 days

### **Average Uplift**
Mean adjusted uplift per triggered trade.

**Formula**: `Average Uplift = Total Uplift / Triggered Trades`

**Example**: $6.94M average per trade

---

## Risk Analysis Terms

### **Stress Test**
Scenario analysis that applies market shocks to test decision robustness. Shows if DIVERT decision still holds under adverse conditions.

### **Stress Scenarios**
1. **Spread Collapse**: JKM-TTF spread narrows by $2.50/MMBtu
2. **Spread Widen**: JKM-TTF spread increases by $2.50/MMBtu
3. **Freight Spike**: Vessel charter costs increase by $10,000/day
4. **Freight Drop**: Vessel charter costs decrease by $10,000/day
5. **EUA Spike**: Carbon prices increase by $10/tonne
6. **Worst Case Combined**: All adverse shocks applied simultaneously

### **Decision Flip**
When a stress scenario changes the decision from DIVERT to KEEP (or vice versa). Indicates sensitivity to that risk factor.

### **Worst Case P&L**
Adjusted uplift under the most adverse stress scenario. Used to understand downside risk.

---

## Configuration Parameters

### **BASIS_ADJUSTMENT**
Percentage haircut applied to raw uplift (default: 0.05 = 5%)

### **OPS_BUFFER_USD**
Operational risk buffer in USD (default: $250,000)

### **DECISION_BUFFER_USD**
Minimum uplift threshold in USD (default: $500,000)

### **COVERAGE_PCT**
Hedge coverage percentage (default: 0.80 = 80%)

### **STRESS_SPREAD_USD**
Spread shock for stress testing (default: $2.50/MMBtu)

### **STRESS_FREIGHT_USD_PER_DAY**
Freight shock for stress testing (default: $10,000/day)

### **STRESS_EUA_USD**
Carbon price shock for stress testing (default: $10/tonne)

---

## Data Sources

### **Yahoo Finance**
Free financial data provider used for:
- TTF prices (ticker: TTF=F)
- EUA carbon prices (ticker: CO2.L)

### **Proxy Data**
Placeholder data used when real historical data unavailable:
- JKM: Calculated as TTF + $2.75 premium
- Freight: Constant $85,000/day
- Fuel: Constant $747/tonne

### **Provenance**
Label indicating whether data is "real" (from Yahoo Finance) or "proxy" (calculated/estimated). Critical for understanding data quality.

---

## File Outputs

### **Trade Pack (JSON)**
Complete decision data including netbacks, hedges, market snapshot. Machine-readable format for APIs and systems.

**Location**: `reports/trade_pack_YYYYMMDD_HHMMSS.json`

### **Trade Ticket (CSV)**
Flat key-value format of decision data for desk review. Human-readable summary for traders.

**Location**: `reports/trade_ticket_YYYYMMDD_HHMMSS.csv`

### **Equity Curve (CSV)**
Historical cumulative P&L over time from backtest.

**Location**: `reports/equity_curve_YYYYMMDD_HHMMSS.csv`

### **Backtest Trades (CSV)**
Complete history of all daily decisions with netbacks, uplifts, and decisions.

**Location**: `reports/backtest_trades_YYYYMMDD_HHMMSS.csv`

### **Stress Pack (CSV)**
Stress test results showing P&L under various adverse scenarios.

**Location**: `reports/stress_pack_YYYYMMDD_HHMMSS.csv`

---

## Common Acronyms

| Acronym | Full Name | Meaning |
|---------|-----------|---------|
| **LNG** | Liquefied Natural Gas | Natural gas cooled to -162°C for transport |
| **TTF** | Title Transfer Facility | European gas price benchmark |
| **JKM** | Japan-Korea Marker | Asian LNG price benchmark |
| **EUA** | European Union Allowance | EU carbon emission permit |
| **EU ETS** | European Union Emissions Trading System | Carbon trading market |
| **MMBtu** | Million British Thermal Units | Energy measurement unit |
| **TFDE** | Tri-Fuel Diesel Electric | LNG vessel propulsion type |
| **MEGI** | M-type Electronically Controlled Gas Injection | Advanced LNG propulsion |
| **P&L** | Profit & Loss | Financial gain or loss |
| **USD** | US Dollars | Currency |
| **tCO₂** | Tonnes of CO₂ | Carbon emissions unit |
| **m³** | Cubic Meters | Volume measurement |
| **kn** | Knots | Speed measurement (nautical miles/hour) |
| **nm** | Nautical Miles | Distance measurement at sea |

---

## Quick Reference

**Decision Logic:**
```
IF Adjusted Uplift ≥ Decision Buffer:
    → DIVERT to Asia
ELSE:
    → KEEP Europe destination
```

**Adjusted Uplift Formula:**
```
Δ_adj = (Asia Netback - Europe Netback) × (1 - Basis Haircut) - Ops Buffer
```

**When to Use:**
- **Live mode** (`python app.py`): Today's decision with current market prices
- **Backtest mode** (`python app.py --backtest`): Historical validation
- **Dashboard** (`python dashboard.py`): Visual interface with all sections

---

*For implementation details, see code documentation in each module.*
