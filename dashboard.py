"""
LNG Cargo Diversion Decision Engine - Terminal Dashboard

Web interface for LNG cargo routing decisions. Shows live market data, netback 
calculations, and hedge instructions. Runs decision logic against current TTF/JKM 
prices to determine whether to send cargo to Europe or Asia. Includes stress tests 
and historical backtest validation.

Dark terminal UI - monospace fonts, flat design, data-dense grids.

Run: python dashboard.py
URL: http://127.0.0.1:8051
"""

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import json

from engine.data_loader import load_routes, load_vessels, load_carbon_params, load_config, load_benchmark_prices, load_aux_series
from engine.market_data import get_market_snapshot
from engine.run import run_trade_decision
from engine.risk import RiskAnalyzer
from engine.backtest import Backtester
from types import SimpleNamespace


# Initialize Dash app with dark theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "LNG Terminal | DevX"

# Terminal-style CSS 
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;500;600;700&display=swap');
            
            :root {
                --terminal-bg: #0a0e1a;
                --terminal-bg-secondary: #111827;
                --terminal-border: #1f2937;
                --terminal-text: #e5e7eb;
                --terminal-text-dim: #9ca3af;
                --terminal-green: #10b981;
                --terminal-red: #ef4444;
                --terminal-amber: #f59e0b;
                --terminal-blue: #3b82f6;
                --terminal-cyan: #06b6d4;
                --grid-border: #1f2937;
            }
            
            body {
                background-color: var(--terminal-bg);
                color: var(--terminal-text);
                font-family: 'Roboto Mono', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
                margin: 0;
                padding: 0;
                overflow-x: hidden;
            }
            
            /* Remove all card styling - flat terminal look */
            .card {
                background-color: var(--terminal-bg-secondary);
                border: 1px solid var(--terminal-border);
                border-radius: 0;
                box-shadow: none;
                margin-bottom: 8px;
            }
            
            .card-body {
                padding: 12px;
            }
            
            /* Header bar - like Bloomberg terminal top bar */
            .terminal-header {
                background-color: #000000;
                border-bottom: 2px solid var(--terminal-amber);
                padding: 8px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-weight: 600;
                letter-spacing: 1px;
            }
            
            .terminal-title {
                color: var(--terminal-amber);
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            
            .terminal-subtitle {
                color: var(--terminal-text-dim);
                font-size: 10px;
                font-weight: 400;
            }
            
            .terminal-timestamp {
                color: var(--terminal-cyan);
                font-size: 11px;
            }
            
            /* Section headers - minimal terminal style */
            .section-header {
                background-color: var(--terminal-border);
                border-left: 3px solid var(--terminal-cyan);
                padding: 6px 12px;
                margin-bottom: 8px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1.5px;
                text-transform: uppercase;
                color: var(--terminal-cyan);
            }
            
            /* Decision badge - terminal style */
            .decision-badge {
                font-family: 'Roboto Mono', monospace;
                font-size: 18px;
                font-weight: 700;
                padding: 8px 24px;
                border-radius: 0;
                letter-spacing: 3px;
                border: 2px solid;
                display: inline-block;
                text-transform: uppercase;
            }
            
            .decision-divert {
                background-color: transparent;
                color: var(--terminal-green);
                border-color: var(--terminal-green);
                box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
            }
            
            .decision-keep {
                background-color: transparent;
                color: var(--terminal-amber);
                border-color: var(--terminal-amber);
                box-shadow: 0 0 10px rgba(245, 158, 11, 0.3);
            }
            
            /* Data tables - dense terminal grid */
            .table {
                font-size: 11px;
                margin-bottom: 0;
                border-collapse: collapse;
            }
            
            .table thead th {
                background-color: var(--terminal-border);
                color: var(--terminal-text-dim);
                font-weight: 600;
                text-transform: uppercase;
                font-size: 10px;
                letter-spacing: 1px;
                padding: 6px 8px;
                border: 1px solid var(--grid-border);
            }
            
            .table tbody td {
                padding: 4px 8px;
                border: 1px solid var(--grid-border);
                background-color: var(--terminal-bg-secondary);
            }
            
            .table tbody tr:hover {
                background-color: rgba(59, 130, 246, 0.1);
            }
            
            /* Monospace numbers with alignment */
            .mono-number {
                font-family: 'Roboto Mono', monospace;
                font-variant-numeric: tabular-nums;
                text-align: right;
                font-weight: 500;
            }
            
            /* Color coding for positive/negative */
            .positive {
                color: var(--terminal-green);
            }
            
            .negative {
                color: var(--terminal-red);
            }
            
            .neutral {
                color: var(--terminal-text-dim);
            }
            
            /* Market data ticker style */
            .market-ticker {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 8px;
                margin-bottom: 8px;
            }
            
            .ticker-item {
                background-color: var(--terminal-bg-secondary);
                border: 1px solid var(--terminal-border);
                border-left: 2px solid var(--terminal-blue);
                padding: 6px 10px;
            }
            
            .ticker-label {
                font-size: 9px;
                color: var(--terminal-text-dim);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                display: block;
                margin-bottom: 2px;
            }
            
            .ticker-value {
                font-size: 13px;
                font-weight: 600;
                color: var(--terminal-text);
                font-variant-numeric: tabular-nums;
            }
            
            .ticker-unit {
                font-size: 9px;
                color: var(--terminal-text-dim);
                margin-left: 4px;
            }
            
            /* Stats grid - data dense */
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 8px;
                margin-bottom: 8px;
            }
            
            .stat-box {
                background-color: var(--terminal-bg-secondary);
                border: 1px solid var(--terminal-border);
                padding: 8px 10px;
            }
            
            .stat-label {
                font-size: 9px;
                color: var(--terminal-text-dim);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
            }
            
            .stat-value {
                font-size: 16px;
                font-weight: 700;
                font-variant-numeric: tabular-nums;
            }
            
            /* Hedge instructions - terminal command style */
            .hedge-command {
                background-color: #000000;
                border: 1px solid var(--terminal-green);
                padding: 10px 12px;
                font-family: 'Roboto Mono', monospace;
                font-size: 12px;
                color: var(--terminal-green);
                margin: 8px 0;
                letter-spacing: 0.5px;
            }
            
            .hedge-command::before {
                content: '> ';
                color: var(--terminal-cyan);
            }
            
            /* Plotly charts - dark theme integration */
            .js-plotly-plot {
                background-color: transparent !important;
            }
            
            /* Remove Bootstrap padding */
            .container-fluid {
                padding: 0;
                max-width: 100%;
            }
            
            .row {
                margin: 0;
            }
            
            .col, [class^="col-"] {
                padding: 4px;
            }
            
            /* Scrollbar - terminal style */
            ::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            
            ::-webkit-scrollbar-track {
                background: var(--terminal-bg);
            }
            
            ::-webkit-scrollbar-thumb {
                background: var(--terminal-border);
                border-radius: 0;
            }
            
            ::-webkit-scrollbar-thumb:hover {
                background: var(--terminal-text-dim);
            }
            
            /* Data provenance tag */
            .provenance-tag {
                display: inline-block;
                font-size: 8px;
                padding: 2px 6px;
                border-radius: 2px;
                margin-left: 6px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .provenance-real {
                background-color: rgba(16, 185, 129, 0.2);
                color: var(--terminal-green);
                border: 1px solid var(--terminal-green);
            }
            
            .provenance-proxy {
                background-color: rgba(245, 158, 11, 0.2);
                color: var(--terminal-amber);
                border: 1px solid var(--terminal-amber);
            }
            
            /* Stress test result indicators */
            .stress-flip {
                background-color: rgba(239, 68, 68, 0.2);
                color: var(--terminal-red);
                padding: 2px 6px;
                font-size: 9px;
                font-weight: 700;
                border: 1px solid var(--terminal-red);
            }
            
            .stress-hold {
                background-color: rgba(16, 185, 129, 0.2);
                color: var(--terminal-green);
                padding: 2px 6px;
                font-size: 9px;
                font-weight: 700;
                border: 1px solid var(--terminal-green);
            }
            
            /* Footer bar */
            .terminal-footer {
                background-color: #000000;
                border-top: 1px solid var(--terminal-border);
                padding: 6px 16px;
                font-size: 9px;
                color: var(--terminal-text-dim);
                text-align: center;
            }
            
            /* Blink animation for live indicator */
            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0.3; }
            }
            
            .live-indicator {
                display: inline-block;
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background-color: var(--terminal-green);
                margin-right: 6px;
                animation: blink 2s infinite;
            }
            
            /* Remove all rounded corners for terminal look */
            * {
                border-radius: 0 !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''


def load_live_decision():
    """Load today's live decision with market data."""
    routes = load_routes()
    vessels = load_vessels()
    carbon_params = load_carbon_params()
    config = load_config()
    
    market_snapshot = get_market_snapshot(config)
    
    trade_pack = run_trade_decision(
        routes=routes,
        vessels=vessels,
        carbon_params=carbon_params,
        load_port="US_Gulf",
        europe_port="Rotterdam",
        asia_port="Tokyo",
        vessel_class="TFDE",
        cargo_capacity_m3=174000,
        ttf_price=market_snapshot.ttf_usd_mmbtu,
        jkm_price=market_snapshot.jkm_usd_mmbtu,
        freight_rate_usd_day=market_snapshot.freight_usd_day,
        fuel_price_usd_t=market_snapshot.fuel_usd_per_t,
        eua_price_usd_t=market_snapshot.eua_usd_per_tco2,
        basis_haircut_pct=float(config["BASIS_ADJUSTMENT"]),
        ops_buffer_usd=float(config["OPS_BUFFER_USD"]),
        decision_buffer_usd=float(config["DECISION_BUFFER_USD"]),
        coverage_pct=float(config["COVERAGE_PCT"]),
        ttf_lot_mmbtu=float(config["TTF_LOT_MMBTU"]),
        jkm_lot_mmbtu=float(config["JKM_LOT_MMBTU"]),
    )
    
    return trade_pack, market_snapshot, config


def load_stress_results(delta_adj, decision):
    """Load stress test results."""
    routes = load_routes()
    vessels = load_vessels()
    carbon_params = load_carbon_params()
    config = load_config()
    
    trade_pack, market_snapshot, _ = load_live_decision()
    
    # Create NetbackCalculator
    from engine.netback import NetbackCalculator
    calculator = NetbackCalculator(routes, vessels, carbon_params)
    
    # Use RiskAnalyzer with proper parameters
    analyzer = RiskAnalyzer(
        netback_calculator=calculator,
        stress_spread_usd=float(config["STRESS_SPREAD_USD"]),
        stress_freight_usd_per_day=float(config["STRESS_FREIGHT_USD_PER_DAY"]),
        stress_eua_usd=float(config["STRESS_EUA_USD"]),
        basis_haircut_pct=float(config["BASIS_ADJUSTMENT"]),
        ops_buffer_usd=float(config["OPS_BUFFER_USD"]),
        decision_buffer_usd=float(config["DECISION_BUFFER_USD"])
    )
    
    # Extract base result from trade_pack
    from engine.decision import DecisionResult
    base_result = DecisionResult(
        delta_netback_raw_usd=trade_pack["decision"]["delta_raw_usd"],
        delta_netback_adj_usd=trade_pack["decision"]["delta_adj_usd"],
        basis_haircut_pct=trade_pack["inputs"]["basis_haircut_pct"],
        ops_buffer_usd=trade_pack["inputs"]["ops_buffer_usd"],
        decision_buffer_usd=trade_pack["inputs"]["decision_buffer_usd"],
        decision=trade_pack["decision"]["decision"],
        hedge_energy_mmbtu=trade_pack["decision"]["hedge_energy_mmbtu"],
        lots_ttf=trade_pack["decision"]["lots_ttf"],
        lots_jkm=trade_pack["decision"]["lots_jkm"]
    )
    
    risk_pack = analyzer.run_stress_test(
        base_result=base_result,
        load_port=trade_pack["inputs"]["load_port"],
        europe_port=trade_pack["inputs"]["europe_port"],
        asia_port=trade_pack["inputs"]["asia_port"],
        vessel_class=trade_pack["inputs"]["vessel_class"],
        cargo_capacity_m3=trade_pack["inputs"]["cargo_capacity_m3"],
        ttf_price=trade_pack["inputs"]["ttf_price"],
        jkm_price=trade_pack["inputs"]["jkm_price"],
        freight_rate_usd_day=trade_pack["inputs"]["freight_rate_usd_day"],
        fuel_price_usd_t=trade_pack["inputs"]["fuel_price_usd_t"],
        eua_price_usd_t=trade_pack["inputs"]["eua_price_usd_t"]
    )
    
    # Convert to list format for table display
    stress_results = []
    for result in risk_pack.stress_results:
        stress_results.append({
            "scenario": result.scenario.name,
            "decision": result.stressed_decision,
            "delta_adj_usd": result.stressed_delta_netback_adj,
            "flipped": result.decision_change
        })
    
    return stress_results


def load_backtest_results():
    """Load backtest results with equity curve."""
    routes = load_routes()
    vessels = load_vessels()
    carbon_params = load_carbon_params()
    config = load_config()
    df_prices = load_benchmark_prices()
    aux_series = load_aux_series()
    historical_data = df_prices.merge(aux_series, on="date")
    
    results = []
    for _, row in historical_data.iterrows():
        trade_pack = run_trade_decision(
            routes=routes,
            vessels=vessels,
            carbon_params=carbon_params,
            load_port="US_Gulf",
            europe_port="Rotterdam",
            asia_port="Tokyo",
            vessel_class="TFDE",
            cargo_capacity_m3=174000,
            ttf_price=row["TTF_USD_MMBTU"],
            jkm_price=row["JKM_USD_MMBTU"],
            freight_rate_usd_day=row["FREIGHT_USD_DAY"],
            fuel_price_usd_t=row["FUEL_USD_PER_T"],
            eua_price_usd_t=row["EUA_USD_PER_TCO2"],
            basis_haircut_pct=float(config["BASIS_ADJUSTMENT"]),
            ops_buffer_usd=float(config["OPS_BUFFER_USD"]),
            decision_buffer_usd=float(config["DECISION_BUFFER_USD"]),
            coverage_pct=float(config["COVERAGE_PCT"]),
            ttf_lot_mmbtu=float(config["TTF_LOT_MMBTU"]),
            jkm_lot_mmbtu=float(config["JKM_LOT_MMBTU"]),
        )
        
        europe_nb = SimpleNamespace(netback_usd=trade_pack["europe"]["netback_usd"])
        asia_nb = SimpleNamespace(netback_usd=trade_pack["asia"]["netback_usd"])
        
        result = SimpleNamespace(
            date=row["date"].date(),
            decision=trade_pack["decision"]["decision"],
            delta_netback_raw_usd=trade_pack["decision"]["delta_raw_usd"],
            delta_netback_adj_usd=trade_pack["decision"]["delta_adj_usd"],
            europe_netback=europe_nb,
            asia_netback=asia_nb,
        )
        results.append(result)
    
    backtester = Backtester()
    bt_results = backtester.run_backtest(results)
    
    return bt_results


def create_terminal_header():
    """Create Bloomberg-style terminal header."""
    now = datetime.now()
    return html.Div([
        html.Div([
            html.Span("LNG DIVERSION ENGINE", className="terminal-title"),
            html.Span(" | USGLF→RTM/TYO", className="terminal-subtitle")
        ], style={"display": "flex", "alignItems": "center", "gap": "12px"}),
        html.Div([
            html.Span(className="live-indicator"),
            html.Span(f"{now.strftime('%Y-%m-%d %H:%M:%S UTC')}", className="terminal-timestamp")
        ], style={"display": "flex", "alignItems": "center"})
    ], className="terminal-header")


def create_market_ticker(market_snapshot):
    """Create market data ticker - terminal style."""
    return html.Div([
        html.Div([
            html.Span("TTF", className="ticker-label"),
            html.Div([
                html.Span(f"${market_snapshot.ttf_usd_mmbtu:.2f}", className="ticker-value"),
                html.Span("/MMBtu", className="ticker-unit"),
                html.Span("REAL" if market_snapshot.provenance.get("TTF") == "real" else "PROXY", 
                         className=f"provenance-tag provenance-{market_snapshot.provenance.get('TTF', 'proxy')}")
            ])
        ], className="ticker-item"),
        
        html.Div([
            html.Span("JKM", className="ticker-label"),
            html.Div([
                html.Span(f"${market_snapshot.jkm_usd_mmbtu:.2f}", className="ticker-value"),
                html.Span("/MMBtu", className="ticker-unit"),
                html.Span("REAL" if market_snapshot.provenance.get("JKM") == "real" else "PROXY", 
                         className=f"provenance-tag provenance-{market_snapshot.provenance.get('JKM', 'proxy')}")
            ])
        ], className="ticker-item"),
        
        html.Div([
            html.Span("EUA", className="ticker-label"),
            html.Div([
                html.Span(f"${market_snapshot.eua_usd_per_tco2:.2f}", className="ticker-value"),
                html.Span("/tCO₂", className="ticker-unit"),
                html.Span("REAL" if market_snapshot.provenance.get("EUA") == "real" else "PROXY", 
                         className=f"provenance-tag provenance-{market_snapshot.provenance.get('EUA', 'proxy')}")
            ])
        ], className="ticker-item"),
        
        html.Div([
            html.Span("FREIGHT", className="ticker-label"),
            html.Div([
                html.Span(f"${market_snapshot.freight_usd_day/1000:.0f}K", className="ticker-value"),
                html.Span("/day", className="ticker-unit"),
                html.Span("PROXY", className="provenance-tag provenance-proxy")
            ])
        ], className="ticker-item"),
        
        html.Div([
            html.Span("FUEL", className="ticker-label"),
            html.Div([
                html.Span(f"${market_snapshot.fuel_usd_per_t:.0f}", className="ticker-value"),
                html.Span("/tonne", className="ticker-unit"),
                html.Span("PROXY", className="provenance-tag provenance-proxy")
            ])
        ], className="ticker-item"),
        
        html.Div([
            html.Span("SPREAD", className="ticker-label"),
            html.Div([
                html.Span(f"${market_snapshot.jkm_usd_mmbtu - market_snapshot.ttf_usd_mmbtu:.2f}", 
                         className=f"ticker-value {'positive' if market_snapshot.jkm_usd_mmbtu > market_snapshot.ttf_usd_mmbtu else 'negative'}"),
                html.Span("/MMBtu", className="ticker-unit")
            ])
        ], className="ticker-item")
    ], className="market-ticker")


def create_decision_section(trade_pack):
    """Create decision display - terminal command style."""
    decision = trade_pack["decision"]["decision"]
    delta_adj = trade_pack["decision"]["delta_adj_usd"]
    
    decision_class = "decision-divert" if decision == "DIVERT" else "decision-keep"
    
    return html.Div([
        html.Div("SECTION 1 | DECISION", className="section-header"),
        html.Div([
            html.Span(decision, className=f"decision-badge {decision_class}"),
            html.Div([
                html.Span("ADJUSTED UPLIFT: ", style={"color": "var(--terminal-text-dim)", "fontSize": "11px"}),
                html.Span(f"${delta_adj/1e6:.2f}M", 
                         style={"fontSize": "18px", "fontWeight": "700", 
                                "color": "var(--terminal-green)" if delta_adj > 0 else "var(--terminal-red)"})
            ], style={"marginTop": "12px"})
        ], style={"padding": "16px 0", "textAlign": "center"})
    ], className="card")


def create_netback_table(trade_pack):
    """Create netback comparison - dense terminal grid."""
    europe = trade_pack["europe"]
    asia = trade_pack["asia"]
    
    return html.Div([
        html.Div("SECTION 2 | NETBACK ANALYSIS", className="section-header"),
        html.Table([
            html.Thead([
                html.Tr([
                    html.Th("ITEM", style={"textAlign": "left"}),
                    html.Th("EUROPE", className="mono-number"),
                    html.Th("ASIA", className="mono-number"),
                    html.Th("DELTA", className="mono-number")
                ])
            ]),
            html.Tbody([
                html.Tr([
                    html.Td("Revenue"),
                    html.Td(f"${europe['revenue_usd']/1e6:.2f}M", className="mono-number"),
                    html.Td(f"${asia['revenue_usd']/1e6:.2f}M", className="mono-number"),
                    html.Td(f"${(asia['revenue_usd'] - europe['revenue_usd'])/1e6:.2f}M", 
                           className=f"mono-number {'positive' if asia['revenue_usd'] > europe['revenue_usd'] else 'negative'}")
                ]),
                html.Tr([
                    html.Td("Voyage Cost"),
                    html.Td(f"-${europe['voyage_cost_usd']/1e6:.2f}M", className="mono-number negative"),
                    html.Td(f"-${asia['voyage_cost_usd']/1e6:.2f}M", className="mono-number negative"),
                    html.Td(f"-${(asia['voyage_cost_usd'] - europe['voyage_cost_usd'])/1e6:.2f}M", 
                           className="mono-number negative")
                ]),
                html.Tr([
                    html.Td("Carbon Cost"),
                    html.Td(f"-${europe['carbon_cost_usd']/1e6:.2f}M", className="mono-number negative"),
                    html.Td(f"-${asia['carbon_cost_usd']/1e6:.2f}M", className="mono-number negative"),
                    html.Td(f"-${(asia['carbon_cost_usd'] - europe['carbon_cost_usd'])/1e6:.2f}M", 
                           className="mono-number negative")
                ]),
                html.Tr([
                    html.Td("NETBACK", style={"fontWeight": "700"}),
                    html.Td(f"${europe['netback_usd']/1e6:.2f}M", className="mono-number positive", style={"fontWeight": "700"}),
                    html.Td(f"${asia['netback_usd']/1e6:.2f}M", className="mono-number positive", style={"fontWeight": "700"}),
                    html.Td(f"${(asia['netback_usd'] - europe['netback_usd'])/1e6:.2f}M", 
                           className=f"mono-number {'positive' if asia['netback_usd'] > europe['netback_usd'] else 'negative'}", 
                           style={"fontWeight": "700"})
                ])
            ])
        ], className="table")
    ], className="card")


def create_hedge_instructions(trade_pack):
    """Create hedge instructions - terminal command style."""
    decision_data = trade_pack["decision"]
    hedge_legs = trade_pack["hedge_legs"]
    coverage_pct = trade_pack["inputs"]["coverage_pct"]
    ttf_price = trade_pack["inputs"]["ttf_price"]
    jkm_price = trade_pack["inputs"]["jkm_price"]
    
    lots_jkm = decision_data["lots_jkm"]
    lots_ttf = decision_data["lots_ttf"]
    hedge_energy = decision_data["hedge_energy_mmbtu"]
    
    # Calculate notionals
    jkm_notional = lots_jkm * 10000 * jkm_price
    ttf_notional = lots_ttf * 10000 * ttf_price
    
    return html.Div([
        html.Div("SECTION 3 | HEDGE EXECUTION", className="section-header"),
        html.Div([
            html.Div(f"{hedge_legs[0]['leg'].upper()} {abs(hedge_legs[0]['lots']):,.0f} LOTS @ MARKET", 
                    className="hedge-command"),
            html.Div(f"{hedge_legs[1]['leg'].upper()} {abs(hedge_legs[1]['lots']):,.0f} LOTS @ MARKET", 
                    className="hedge-command"),
            html.Div([
                html.Div([
                    html.Span("Coverage:", className="stat-label"),
                    html.Div(f"{coverage_pct*100:.0f}%", className="stat-value")
                ], className="stat-box"),
                html.Div([
                    html.Span("JKM Notional:", className="stat-label"),
                    html.Div(f"${abs(jkm_notional)/1e6:.1f}M", className="stat-value positive")
                ], className="stat-box"),
                html.Div([
                    html.Span("TTF Notional:", className="stat-label"),
                    html.Div(f"${abs(ttf_notional)/1e6:.1f}M", className="stat-value negative")
                ], className="stat-box")
            ], className="stats-grid")
        ])
    ], className="card")


def create_stress_table(stress_results):
    """Create stress test table - dense grid."""
    return html.Div([
        html.Div("SECTION 4 | STRESS TESTING", className="section-header"),
        html.Table([
            html.Thead([
                html.Tr([
                    html.Th("SCENARIO", style={"textAlign": "left"}),
                    html.Th("DECISION", className="mono-number"),
                    html.Th("ADJ UPLIFT", className="mono-number"),
                    html.Th("STATUS", style={"textAlign": "center"})
                ])
            ]),
            html.Tbody([
                html.Tr([
                    html.Td(result["scenario"]),
                    html.Td(result["decision"], className="mono-number", 
                           style={"color": "var(--terminal-green)" if result["decision"] == "DIVERT" else "var(--terminal-amber)"}),
                    html.Td(f"${result['delta_adj_usd']/1e6:.2f}M", 
                           className=f"mono-number {'positive' if result['delta_adj_usd'] > 0 else 'negative'}"),
                    html.Td(
                        html.Span("FLIP" if result.get("flipped", False) else "HOLD", 
                                 className="stress-flip" if result.get("flipped", False) else "stress-hold"),
                        style={"textAlign": "center"}
                    )
                ]) for result in stress_results
            ])
        ], className="table")
    ], className="card")


def create_backtest_section(bt_results):
    """Create backtest metrics - data dense stats."""
    total_days = len(bt_results.decision_history)
    triggered = bt_results.decision_history['triggered'].sum()
    avg_uplift = bt_results.decision_history[bt_results.decision_history['triggered'] == 1]['delta_netback_adj_usd'].mean()
    total_uplift = bt_results.decision_history[bt_results.decision_history['triggered'] == 1]['delta_netback_adj_usd'].sum()
    min_uplift = bt_results.decision_history[bt_results.decision_history['triggered'] == 1]['delta_netback_adj_usd'].min()
    max_uplift = bt_results.decision_history[bt_results.decision_history['triggered'] == 1]['delta_netback_adj_usd'].max()
    
    return html.Div([
        html.Div("SECTION 5 | RULE VALIDATION (BACKTEST)", className="section-header"),
        html.Div([
            html.Div([
                html.Span("Observation Period:", className="stat-label"),
                html.Div(f"{total_days} days", className="stat-value")
            ], className="stat-box"),
            html.Div([
                html.Span("DIVERT Frequency:", className="stat-label"),
                html.Div(f"{triggered} ({triggered/total_days*100:.1f}%)", 
                        className="stat-value positive")
            ], className="stat-box"),
            html.Div([
                html.Span("KEEP Frequency:", className="stat-label"),
                html.Div(f"{total_days - triggered} ({(1-triggered/total_days)*100:.1f}%)", 
                        className="stat-value neutral")
            ], className="stat-box"),
            html.Div([
                html.Span("Avg Conditional Uplift:", className="stat-label"),
                html.Div(f"${avg_uplift/1e6:.2f}M", className="stat-value positive")
            ], className="stat-box"),
            html.Div([
                html.Span("Total Conditional Uplift:", className="stat-label"),
                html.Div(f"${total_uplift/1e9:.2f}B", className="stat-value positive")
            ], className="stat-box"),
            html.Div([
                html.Span("Min Uplift:", className="stat-label"),
                html.Div(f"${min_uplift/1e6:.2f}M", className="stat-value")
            ], className="stat-box"),
            html.Div([
                html.Span("Max Uplift:", className="stat-label"),
                html.Div(f"${max_uplift/1e6:.2f}M", className="stat-value")
            ], className="stat-box")
        ], className="stats-grid"),
        html.Div([
            html.Span("⚠ ", style={"color": "var(--terminal-amber)"}),
            html.Span("Rule validation only. Not trading P&L. Excludes execution slippage, basis risk, hedging costs.",
                     style={"fontSize": "9px", "color": "var(--terminal-text-dim)"})
        ], style={"marginTop": "8px", "padding": "8px", "borderLeft": "2px solid var(--terminal-amber)"})
    ], className="card")


def create_equity_chart(bt_results):
    """Create equity curve - terminal dark theme."""
    df = bt_results.equity_curve
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["cumulative_pnl"] / 1e6,
        mode="lines",
        name="Cumulative Uplift",
        line=dict(color="#10b981", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(16, 185, 129, 0.1)"
    ))
    
    fig.update_layout(
        plot_bgcolor="#0a0e1a",
        paper_bgcolor="#111827",
        font=dict(family="Roboto Mono, monospace", size=10, color="#9ca3af"),
        xaxis=dict(
            showgrid=True,
            gridcolor="#1f2937",
            zeroline=False,
            title="Date",
            title_font=dict(size=10)
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#1f2937",
            zeroline=True,
            zerolinecolor="#1f2937",
            title="Cumulative Uplift ($M)",
            title_font=dict(size=10)
        ),
        margin=dict(l=40, r=20, t=20, b=40),
        height=300,
        hovermode="x unified",
        showlegend=False
    )
    
    return html.Div([
        html.Div("EQUITY CURVE", className="section-header"),
        dcc.Graph(figure=fig, config={"displayModeBar": False})
    ], className="card")


# App layout
app.layout = html.Div([
    create_terminal_header(),
    
    dcc.Interval(
        id='interval-component',
        interval=15*60*1000,  # 15 minutes
        n_intervals=0
    ),
    
    html.Div([
        # Market ticker
        html.Div(id="market-ticker-container", style={"padding": "8px"}),
        
        # Main content grid
        html.Div([
            # Left column - Decision + Netback + Hedge
            html.Div([
                html.Div(id="decision-container"),
                html.Div(id="netback-container"),
                html.Div(id="hedge-container")
            ], style={"padding": "4px"}, className="col-md-6"),
            
            # Right column - Stress + Backtest
            html.Div([
                html.Div(id="stress-container"),
                html.Div(id="backtest-container"),
                html.Div(id="equity-container")
            ], style={"padding": "4px"}, className="col-md-6")
        ], className="row")
    ], className="container-fluid", style={"padding": "4px"}),
    
    html.Div([
        html.Span("LNG DIVERSION ENGINE | ", style={"fontWeight": "600"}),
        html.Span("Data: Yahoo Finance (TTF, EUA 15-20min delay) | "),
        html.Span("JKM Proxy: TTF + Variable Premium | "),
        html.Span("Auto-refresh: 15min | "),
        html.Span(f"© {datetime.now().year} DevX")
    ], className="terminal-footer")
], style={"minHeight": "100vh", "display": "flex", "flexDirection": "column"})


@app.callback(
    [Output("market-ticker-container", "children"),
     Output("decision-container", "children"),
     Output("netback-container", "children"),
     Output("hedge-container", "children"),
     Output("stress-container", "children"),
     Output("backtest-container", "children"),
     Output("equity-container", "children")],
    [Input("interval-component", "n_intervals")]
)
def update_dashboard(n):
    """Update all dashboard sections."""
    # Load live decision
    trade_pack, market_snapshot, config = load_live_decision()
    
    # Load stress tests
    stress_results = load_stress_results(trade_pack["decision"]["delta_adj_usd"], trade_pack["decision"]["decision"])
    
    # Load backtest (cached, only loads once)
    bt_results = load_backtest_results()
    
    return (
        create_market_ticker(market_snapshot),
        create_decision_section(trade_pack),
        create_netback_table(trade_pack),
        create_hedge_instructions(trade_pack),
        create_stress_table(stress_results),
        create_backtest_section(bt_results),
        create_equity_chart(bt_results)
    )


if __name__ == "__main__":
    print("\n" + "="*80)
    print("LNG DIVERSION ENGINE | TERMINAL DASHBOARD")
    print("="*80)
    print("Starting server on http://127.0.0.1:8051")
    print("Financial terminal UI | Dark mode | Data-dense layout")
    print("Press Ctrl+C to stop")
    print("="*80 + "\n")
    
    app.run(debug=True, host="0.0.0.0", port=8051)
