# LNG Cargo Diversion Decision Engine

## What This Solves

**The Desk Decision:** You have an LNG cargo leaving the US Gulf Coast. The original plan is to discharge in Europe (Rotterdam, TTF market). But Asia (Tokyo, JKM market) prices might be higher. Should you divert?

This engine answers three critical questions:
1. **Which route is more profitable?** Compare Europe vs Asia netbacks (profit after all costs)
2. **Is the margin large enough to act?** Apply conservative buffers for basis risk and operational uncertainty
3. **What's the trade?** Generate executable hedge instructions (futures lots, price levels)

**For whom:** Front office LNG traders, risk managers, and operations teams evaluating cargo routing decisions in real-time.

**Output:** A clear DIVERT or KEEP decision with supporting analytics, stress tests, and historical validation.
---

## Decision Rule

The engine calculates the **adjusted uplift** (extra profit from diverting to Asia) and triggers DIVERT if it exceeds a threshold:

```
Raw Uplift = Asia Netback - Europe Netback

Adjusted Uplift = Raw Uplift × (1 - Basis Haircut) - Ops Buffer

Decision: DIVERT if Adjusted Uplift ≥ Decision Buffer
         KEEP otherwise
```

**Why the buffers?**
- **Basis Haircut (5%)**: Accounts for basis risk between physical LNG prices and futures prices, timing mismatches, and execution slippage
- **Ops Buffer ($250k)**: Covers operational risks like port delays, weather, demurrage, canal wait times
- **Decision Buffer ($500k)**: Minimum profit threshold to justify operational complexity of diversion

**Example:**
```
Asia Netback:    $134.5M
Europe Netback:  $126.8M
Raw Uplift:      $7.7M

Adjusted Uplift: $7.7M × 0.95 - $250k = $7.06M
Decision:        DIVERT ✓ (exceeds $500k threshold)
```

---

## Inputs

### Real-Time Market Data (Auto-fetched)
| Data Point | Source | Status |
|------------|--------|--------|
| **TTF** (European gas) | Yahoo Finance (TTF=F) | Real |
| **EUA** (Carbon allowances) | Yahoo Finance (CO2.L) | Real |
| **JKM** (Asian LNG) | TTF + $2.75 premium | Proxy |
| **Freight Rate** | Constant $85k/day | Proxy |
| **Fuel Price** | Constant $747/tonne | Proxy |

### Static/Configuration Data (CSV files in `data/`)
- **Routes** (`routes.csv`): Distances in nautical miles (US Gulf → Rotterdam: 5,000 nm, US Gulf → Tokyo: 9,500 nm)
- **Vessels** (`vessels.csv`): TFDE/MEGI specs (capacity 174k m³, speed 19.5 kn, boil-off 0.10%/day, fuel consumption)
- **Carbon Params** (`carbon_params.csv`): CO₂ emission factors (3.114 tCO₂/tonne fuel)
- **Config** (`config.csv`): Decision buffers, basis haircut, coverage %, stress test parameters

---

## Outputs

### 1. Decision & Trade Ticket
**Live evaluation** generates:
- **Decision**: DIVERT or KEEP with adjusted uplift in USD
- **Netbacks**: Europe and Asia profit calculations with cost breakdowns
- **Hedge Instructions**: 
  - Example: `BUY JKM 322 lots | SELL TTF 322 lots`
  - Sized at 80% coverage (configurable)
  - 1 lot = 10,000 MMBtu

**Saved to:** `reports/trade_ticket_YYYYMMDD_HHMMSS.csv` (when using `--save`)

### 2. Risk Analysis (Stress Testing)
Tests decision robustness under adverse scenarios:
- Spread collapse (JKM-TTF narrows by $2.50/MMBtu)
- Spread widening (JKM-TTF increases by $2.50/MMBtu)
- Freight spike (+$10k/day charter cost)
- Freight drop (-$10k/day)
- EUA spike (+$10/tonne carbon)
- Worst case combined (all adverse shocks together)

**Output:** Shows if decision flips under stress, worst-case P&L

### 3. Historical Validation (Backtest)
Runs decision rule on 530+ days of historical data (Jan 2024 - present):

**Metrics:**
- **Hit Rate**: % of days DIVERT was triggered (e.g., 100% = always profitable to divert)
- **Average Uplift**: Mean profit per triggered trade (e.g., $6.94M)
- **Total Uplift**: Cumulative profit across all trades (e.g., $3.68B)
- **Sharpe Ratio**: Risk-adjusted returns, annualized (e.g., 439.74 = extremely consistent)
- **Max Drawdown**: Largest peak-to-trough loss (e.g., $0 = no losing days)
- **Equity Curve**: Chart showing cumulative P&L over time

**Saved to:** 
- `reports/backtest_report_YYYYMMDD_HHMMSS.json`
- `reports/equity_curve_YYYYMMDD_HHMMSS.csv`

### 4. Dashboard (Web Interface)
Visual interface showing all above outputs in one page:
- Today's decision with market snapshot
- Trade ticket with hedge legs
- Stress test table
- Historical performance (KPIs + equity curve chart)
- Auto-refreshes every 15 minutes while open

---

## How to Run

### Setup (One-time)
```bash
# Clone repo and navigate to directory
cd lng-cargo-diversion-engine

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download historical data for backtesting
python tools/download_historical_data.py
```

### CLI Usage

**1. Live Decision (Today's Market Data)**
```bash
python app.py
```
Fetches current TTF and EUA from Yahoo Finance, calculates decision, prints to console.

**2. Live Decision + Save Reports**
```bash
python app.py --save
```
Same as above, but saves trade ticket and trade pack JSON to `reports/`.

**3. Backtest Mode (Historical Validation)**
```bash
python app.py --backtest --save
```
Runs decision engine on all 530+ days of historical data, displays metrics, saves equity curve and trade history.

**4. Custom Parameters**
```bash
# Change route or vessel
python app.py --asia-port Singapore --vessel-class MEGI

# Override decision parameters
python app.py --basis 0.03 --ops-buffer 200000 --decision-buffer 600000

# Full custom run with save
python app.py --asia-port Singapore --basis 0.04 --save
```

### Dashboard Usage

**Start the dashboard:**
```bash
.venv/bin/python dashboard.py
```

**Access:** Open browser to `http://127.0.0.1:8050`

**Features:**
- Fresh market data on every page load
- Auto-refreshes every 15 minutes while open
- Backtest cached at startup (fast load after first time)
- Single-page scroll layout (no tabs)

**To stop:** Press `Ctrl+C` in terminal

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--load-port` | Load port | US_Gulf |
| `--europe-port` | Europe discharge port | Rotterdam |
| `--asia-port` | Asia discharge port | Tokyo |
| `--vessel-class` | Vessel class (TFDE/MEGI) | TFDE |
| `--cargo-m3` | Cargo capacity in m³ | 174000 |
| `--basis` | Basis haircut 0-1 (e.g., 0.05) | 0.05 |
| `--ops-buffer` | Ops buffer in USD | 250000 |
| `--decision-buffer` | Decision buffer in USD | 500000 |
| `--coverage` | Coverage ratio 0-1 (e.g., 0.80) | 0.80 |
| `--save` | Save results to reports/ | False |
| `--backtest` | Run backtest mode | False |

---

## Assumptions & Limitations

### Current Assumptions
1. **JKM Proxy**: Calculated as TTF + $2.75 premium. Real JKM requires Platts subscription ($$$).
2. **Freight Proxy**: Constant $85,000/day. Real freight rates (Baltic Exchange LNG indices) require subscription.
3. **Fuel Proxy**: Constant $747/tonne LNG bunker fuel. Real bunker prices require subscription or broker quotes.
4. **Boil-off**: Fixed 0.10%/day. Actual boil-off varies by vessel age, insulation, ambient conditions.
5. **Voyage Time**: Based on great-circle distance and constant speed. Ignores weather routing, canal delays, port congestion.
6. **No Canal Costs**: Suez/Panama canal fees not explicitly modeled (can be added to ops buffer).
7. **Single Cargo Model**: One-way laden voyage. Doesn't optimize ballast leg or round-trip economics.
8. **Static Vessel Selection**: Doesn't optimize vessel choice based on current market conditions.

### Known Limitations
- **No weather routing**: Uses straight-line distance, not actual navigation paths
- **No port logistics**: Assumes immediate discharge, no berth availability constraints
- **No contract basis risk**: Assumes perfect hedge execution at settlement prices
- **No credit/margin modeling**: Doesn't account for exchange margin requirements or credit lines
- **No multi-cargo optimization**: Evaluates single cargo in isolation

### Operational Uncertainties (Covered by Buffers)
- Laycan slippage (loading date delays)
- Terminal delays and demurrage
- Weather deviations
- Bunkering strategy variations
- Port congestion and wait times

**These are handled via the $250k Ops Buffer rather than explicit scheduling models.**

---

## How to Swap in Licensed Feeds

When you have access to professional data feeds, replace proxies with real data:

### Option 1: Swap Yahoo Finance for Bloomberg/Refinitiv
In `engine/market_data.py`:
```python
# Current: Yahoo Finance
ttf = _last_close("TTF=F")

# Replace with Bloomberg API
import blpapi
ttf = fetch_bloomberg("TTF Comdty", "PX_LAST")
```

### Option 2: Add Real JKM from Platts
In `engine/market_data.py`:
```python
# Current: Proxy
jkm = ttf + 2.75

# Replace with Platts API
jkm = fetch_platts_jkm()  # Your Platts integration
prov["JKM"] = "real"
```

### Option 3: Add Real Freight from Baltic Exchange
In `data/config.csv` or via API:
```python
# Current: Constant
freight = 85000

# Replace with Baltic LNG7t index
freight = fetch_baltic_lng7t()  # Your Baltic integration
```

### Option 4: Use Real Bunker Prices
```python
# Current: Constant
fuel = 747

# Replace with bunker broker feed
fuel = fetch_bunker_prices("VLSFO", "Singapore")
```

**Data Contracts:** All modules expect prices in standard units (USD/MMBtu, USD/day, USD/tonne). No code changes needed beyond swapping the data fetch function.

---

## Screenshots

### 1. Dashboard - Today's Decision & Trade Ticket
![Dashboard Decision and Trade Ticket](docs/screenshots/1-dashboard-decision-ticket.png)
*Shows live decision (DIVERT/KEEP), adjusted uplift, netback comparison, market snapshot with provenance, and hedge instructions*

### 2. Dashboard - Risk Analysis (Stress Pack)
![Dashboard Stress Testing](docs/screenshots/2-dashboard-stress-pack.png)
*Stress test scenarios showing decision robustness under spread collapse, freight spikes, and carbon shocks*

### 3. Dashboard - Historical Validation (Backtest)
![Dashboard Backtest Results](docs/screenshots/3-dashboard-backtest-equity.png)
*Performance metrics (hit rate, Sharpe ratio, total uplift) and equity curve from 530+ days of historical data*

### 4. CLI - Trade Note Output
![CLI Trade Note](docs/screenshots/4-cli-trade-note.png)

*Command-line output showing decision with all calculations and hedge sizing*

---
