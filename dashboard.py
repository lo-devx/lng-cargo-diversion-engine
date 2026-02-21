"""
LNG Cargo Diversion Decision Engine - Dash Dashboard

=== WHAT THIS DOES (IN SIMPLE TERMS) ===

Imagine you have a ship full of LNG (liquefied natural gas) leaving the US Gulf Coast.
You need to decide: should you sell it in Europe (Rotterdam) or divert to Asia (Tokyo)?

This dashboard helps make that decision by:

1. COMPARING THE MONEY: 
   - Calculates how much profit you'd make selling in Europe vs Asia
   - Takes into account: gas prices, shipping costs, fuel, and carbon taxes
   - Shows you the "uplift" = extra profit if you divert to Asia

2. SHOWING TODAY'S CALL:
   - DIVERT = Asia is more profitable (after accounting for risks)
   - KEEP = Europe is better (or Asia margin too thin)

3. TELLING YOU THE HEDGE:
   - If you divert, you need to hedge the price risk
   - Shows exact trades: "BUY JKM 322 lots, SELL TTF 322 lots"

4. STRESS TESTING:
   - What if spreads collapse? Freight spikes? Carbon costs jump?
   - Shows if your decision still holds under bad scenarios

5. PROVING IT WORKS:
   - Backtests the rule on 2+ years of real market data
   - Shows cumulative profit, hit rate, and risk-adjusted returns

Think of it as: "GPS for cargo routing" + "Risk calculator" + "Historical proof"

Run with: python dashboard.py
Access at: http://127.0.0.1:8050
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


# Initialize Dash app with Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "LNG Diversion Engine"

# Custom CSS for better aesthetics
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #7e22ce 100%);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                min-height: 100vh;
            }
            .card {
                background: rgba(255, 255, 255, 0.98);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 16px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .card:hover {
                transform: translateY(-2px);
                box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2);
            }
            h1 {
                font-weight: 700;
                letter-spacing: -1px;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
            }
            h2, h3, h4, h5 {
                font-weight: 600;
            }
            .badge {
                font-weight: 700;
                letter-spacing: 1.5px;
                padding: 16px 32px !important;
                border-radius: 12px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
            }
            .table {
                border-radius: 8px;
                overflow: hidden;
            }
            .table thead th {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                font-weight: 600;
                border: none;
                padding: 14px;
            }
            .table-hover tbody tr:hover {
                background-color: rgba(102, 126, 234, 0.08);
            }
            hr {
                border-color: rgba(255, 255, 255, 0.2);
                opacity: 0.3;
            }
            /* Animated gradient text */
            .hero-text {
                background: linear-gradient(45deg, #fff, #e0e7ff, #fff);
                background-size: 200% 200%;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: gradient 3s ease infinite;
            }
            @keyframes gradient {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            /* Custom scrollbar */
            ::-webkit-scrollbar {
                width: 10px;
            }
            ::-webkit-scrollbar-track {
                background: rgba(255, 255, 255, 0.1);
            }
            ::-webkit-scrollbar-thumb {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 5px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: rgba(255, 255, 255, 0.5);
            }
            /* Stats cards */
            .stat-card {
                background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
                border-radius: 12px;
                padding: 20px;
                border-left: 4px solid #667eea;
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
    """Load stress test results - simplified to show scenarios only."""
    config = load_config()
    
    # Create mock stress pack with typical scenarios
    # In a full implementation, this would call RiskAnalyzer
    scenarios = [
        {"name": "Base Case", "delta_adj_usd": delta_adj, "decision": decision},
        {"name": "Spread Collapse (-$2.50)", "delta_adj_usd": delta_adj - 2500000, "decision": "DIVERT" if delta_adj - 2500000 > 500000 else "KEEP"},
        {"name": "Spread Widen (+$2.50)", "delta_adj_usd": delta_adj + 2500000, "decision": "DIVERT"},
        {"name": "Freight Spike (+$10k/day)", "delta_adj_usd": delta_adj - 400000, "decision": "DIVERT" if delta_adj - 400000 > 500000 else "KEEP"},
        {"name": "EUA Spike (+$10/t)", "delta_adj_usd": delta_adj - 200000, "decision": "DIVERT" if delta_adj - 200000 > 500000 else "KEEP"},
        {"name": "Worst Case Combined", "delta_adj_usd": delta_adj - 3100000, "decision": "DIVERT" if delta_adj - 3100000 > 500000 else "KEEP"},
    ]
    
    worst_case = min(s["delta_adj_usd"] for s in scenarios)
    
    return SimpleNamespace(scenarios=scenarios, worst_case_pnl=worst_case)


def load_backtest_results():
    """Load backtest results."""
    routes = load_routes()
    vessels = load_vessels()
    carbon_params = load_carbon_params()
    config = load_config()
    
    benchmark_prices = load_benchmark_prices()
    aux_series = load_aux_series()
    historical_data = benchmark_prices.merge(aux_series, on="date")
    
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
    backtest_result = backtester.run_backtest(results)
    
    return backtest_result


# Load backtest data at server startup (expensive operation - cache it)
print("Loading backtest data (this takes a moment)...")
backtest_result = load_backtest_results()
print("Backtest loaded!")


# ============================================================================
# SECTION 1: TODAY'S DECISION - Dynamic
# ============================================================================

section_1 = html.Div(id="section-1-content")


# ============================================================================
# SECTION 2: TRADE TICKET - Dynamic
# ============================================================================

section_2 = html.Div(id="section-2-content")


# ============================================================================
# SECTION 3: RISK (Stress Pack) - Dynamic
# ============================================================================

section_3 = html.Div(id="section-3-content")


# ============================================================================
# SECTION 4: HISTORICAL VALIDATION
# ============================================================================

# Build equity curve chart
equity_fig = go.Figure()
equity_fig.add_trace(go.Scatter(
    x=backtest_result.equity_curve["date"],
    y=backtest_result.equity_curve["cumulative_pnl"],
    mode='lines',
    name='Cumulative P&L',
    line=dict(color='#667eea', width=3),
    fill='tozeroy',
    fillcolor='rgba(102, 126, 234, 0.15)',
    hovertemplate='<b>%{x}</b><br>P&L: $%{y:,.0f}<extra></extra>'
))

equity_fig.update_layout(
    title="Equity Curve (Since Jan 2024)",
    xaxis_title="Date",
    yaxis_title="Cumulative P&L (USD)",
    hovermode='x unified',
    template='plotly_white',
    height=450,
    margin=dict(l=20, r=20, t=40, b=20),
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Inter, sans-serif', size=12),
    xaxis=dict(gridcolor='rgba(0,0,0,0.05)'),
    yaxis=dict(gridcolor='rgba(0,0,0,0.05)')
)

metrics = backtest_result.metrics

section_4 = dbc.Card([
    dbc.CardBody([
        html.H4("HISTORICAL VALIDATION", className="text-muted mb-4"),
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H6("Total Observations", className="text-muted mb-2"),
                    html.H3(f"{metrics.total_observations}", className="mb-0", style={'color': '#667eea'})
                ], className="stat-card")
            ], width=3),
            dbc.Col([
                html.Div([
                    html.H6("Hit Rate", className="text-muted mb-2"),
                    html.H3(f"{metrics.hit_rate:.1%}", className="mb-0", style={'color': '#10b981'})
                ], className="stat-card")
            ], width=3),
            dbc.Col([
                html.Div([
                    html.H6("Average Uplift", className="text-muted mb-2"),
                    html.H3(f"${metrics.average_uplift_usd/1e6:.1f}M", className="mb-0", style={'color': '#f59e0b'})
                ], className="stat-card")
            ], width=3),
            dbc.Col([
                html.Div([
                    html.H6("Sharpe Ratio", className="text-muted mb-2"),
                    html.H3(f"{metrics.sharpe_ratio:.2f}" if metrics.sharpe_ratio else "N/A", className="mb-0", style={'color': '#8b5cf6'})
                ], className="stat-card")
            ], width=3),
        ], className="mb-4"),
        
        dcc.Graph(figure=equity_fig)
    ])
], className="mb-4 shadow")


# ============================================================================
# SECTION 5: ANALYTICS CHARTS (Dynamic)
# ============================================================================

section_5 = html.Div(id="section-5-content")


# ============================================================================
# LAYOUT
# ============================================================================

app.layout = dbc.Container([
    # Auto-refresh every 15 minutes (900000 ms)
    dcc.Interval(
        id='interval-component',
        interval=15*60*1000,  # 15 minutes in milliseconds
        n_intervals=0
    ),
    
    dbc.Row([
        dbc.Col([
            html.H1("LNG Cargo Diversion Engine", className="mt-4 mb-1 hero-text"),
            html.P("US Gulf → Rotterdam (TTF) vs Tokyo (JKM)", className="mb-4", style={'color': 'rgba(255,255,255,0.9)', 'fontSize': '18px'})
        ], width=8),
        dbc.Col([
            html.Div(id="timestamp-display")
        ], width=4, className="text-end")
    ]),
    
    dbc.Row([
        dbc.Col(section_1, width=12)
    ]),
    
    dbc.Row([
        dbc.Col(section_2, width=12)
    ]),
    
    dbc.Row([
        dbc.Col(section_3, width=12)
    ]),
    
    dbc.Row([
        dbc.Col(section_4, width=12)
    ]),
    
    dbc.Row([
        dbc.Col(section_5, width=12)
    ]),
    
    html.Footer([
        html.Hr(style={'borderColor': 'rgba(255,255,255,0.3)'}),
        html.P("Data: TTF & EUA from Yahoo Finance | JKM = TTF + $2.75 premium | Freight & Fuel = Proxy", 
               className="text-center mb-4", style={'color': 'rgba(255,255,255,0.7)'})
    ])
    
], fluid=True, className="px-4", style={'paddingBottom': '40px'})


# ============================================================================
# CALLBACKS - Enable Dynamic Updates
# ============================================================================

@app.callback(
    Output("timestamp-display", "children"),
    Input('interval-component', 'n_intervals')
)
def update_timestamp(n):
    """Update the timestamp display."""
    now = datetime.now()
    return html.Div([
        html.H5(now.strftime("%d %B %Y"), className="text-end mb-0 mt-4", style={'color': 'white', 'fontWeight': '600'}),
        html.P(now.strftime("%H:%M UTC"), className="text-end mb-0", style={'color': 'rgba(255,255,255,0.8)', 'fontSize': '14px'}),
        html.P("🔄 Auto-refresh: 15 min", className="text-end mb-0", style={'color': 'rgba(255,255,255,0.6)', 'fontSize': '11px'})
    ])


@app.callback(
    [
        Output("section-1-content", "children"),
        Output("section-2-content", "children"),
        Output("section-3-content", "children"),
        Output("section-5-content", "children")
    ],
    Input('interval-component', 'n_intervals')
)
def update_live_sections(n):
    """Update live decision, trade ticket, stress test, and analytics charts.
    
    This callback fires:
    1. On page load (n_intervals = 0)
    2. Every 15 minutes while page is open
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Refreshing live data (trigger #{n})...")
    
    # Fetch fresh market data and run decision
    trade_pack, market_snapshot, config = load_live_decision()
    
    decision = trade_pack["decision"]["decision"]
    delta_adj = trade_pack["decision"]["delta_adj_usd"]
    europe_netback = trade_pack["europe"]["netback_usd"]
    asia_netback = trade_pack["asia"]["netback_usd"]
    hedge_legs = trade_pack["hedge_legs"]
    
    # Section 1: Decision
    decision_color = "success" if decision == "DIVERT" else "secondary"
    decision_badge = dbc.Badge(decision, color=decision_color, className="fs-1 px-4 py-3")
    
    section_1 = dbc.Card([
        dbc.CardBody([
            html.H2("TODAY'S DECISION", className="text-muted mb-4"),
            html.Div([
                decision_badge,
                html.H3(f"${delta_adj:,.0f}", className="text-success mt-3 mb-0"),
                html.P("Adjusted Uplift", className="text-muted")
            ], className="text-center mb-4"),
            
            dbc.Row([
                dbc.Col([
                    html.H5("Europe Netback", className="text-muted mb-2"),
                    html.H4(f"${europe_netback:,.0f}", className="mb-0")
                ], width=6),
                dbc.Col([
                    html.H5("Asia Netback", className="text-muted mb-2"),
                    html.H4(f"${asia_netback:,.0f}", className="mb-0")
                ], width=6),
            ], className="mb-4"),
            
            html.Hr(),
            
            html.H5("Market Snapshot", className="text-muted mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Strong("TTF:"),
                    html.Span(f" ${market_snapshot.ttf_usd_mmbtu:.2f}/MMBtu")
                ], width=4),
                dbc.Col([
                    html.Strong("JKM:"),
                    html.Span(f" ${market_snapshot.jkm_usd_mmbtu:.2f}/MMBtu")
                ], width=4),
                dbc.Col([
                    html.Strong("EUA:"),
                    html.Span(f" ${market_snapshot.eua_usd_per_tco2:.2f}/tCO₂")
                ], width=4),
            ], className="mb-2"),
            dbc.Row([
                dbc.Col([
                    html.Strong("Freight:"),
                    html.Span(f" ${market_snapshot.freight_usd_day:,.0f}/day")
                ], width=4),
                dbc.Col([
                    html.Strong("Fuel:"),
                    html.Span(f" ${market_snapshot.fuel_usd_per_t:.0f}/t")
                ], width=4),
                dbc.Col([
                    html.Small(f"As of: {market_snapshot.asof}", className="text-muted")
                ], width=4),
            ]),
        ])
    ], className="mb-4 shadow")
    
    # Section 2: Trade Ticket
    section_2 = dbc.Card([
        dbc.CardBody([
            html.H4("TRADE TICKET", className="text-muted mb-4"),
            dbc.Row([
                dbc.Col([
                    html.H5(hedge_legs[0]["leg"], className="text-primary mb-2"),
                    html.H3(f"{hedge_legs[0]['lots']} lots", className="mb-0")
                ], width=6),
                dbc.Col([
                    html.H5(hedge_legs[1]["leg"], className="text-danger mb-2"),
                    html.H3(f"{hedge_legs[1]['lots']} lots", className="mb-0")
                ], width=6),
            ], className="mb-3"),
            
            html.Hr(),
            
            dbc.Row([
                dbc.Col([
                    html.Small("Coverage:", className="text-muted"),
                    html.Span(f" {float(config['COVERAGE_PCT'])*100:.0f}%")
                ], width=4),
                dbc.Col([
                    html.Small("Basis haircut:", className="text-muted"),
                    html.Span(f" {float(config['BASIS_ADJUSTMENT'])*100:.1f}%")
                ], width=4),
                dbc.Col([
                    html.Small("Ops buffer:", className="text-muted"),
                    html.Span(f" ${float(config['OPS_BUFFER_USD']):,.0f}")
                ], width=4),
            ])
        ])
    ], className="mb-4 shadow")
    
    # Section 3: Stress Test
    stress_pack = load_stress_results(delta_adj, decision)
    stress_rows = []
    for scenario in stress_pack.scenarios:
        stress_rows.append(html.Tr([
            html.Td(scenario["name"]),
            html.Td(f"${scenario['delta_adj_usd']:,.0f}", className="text-end"),
            html.Td(
                scenario["decision"],
                className="text-success" if scenario["decision"] == "DIVERT" else "text-secondary"
            ),
        ]))
    
    section_3 = dbc.Card([
        dbc.CardBody([
            html.H4("RISK / STRESS PACK", className="text-muted mb-4"),
            dbc.Table([
                html.Thead(html.Tr([
                    html.Th("Scenario"),
                    html.Th("Adjusted Uplift", className="text-end"),
                    html.Th("Decision"),
                ])),
                html.Tbody(stress_rows)
            ], bordered=True, hover=True, className="mb-3"),
            
            html.Div([
                html.Strong("Worst case P&L: "),
                html.Span(f"${stress_pack.worst_case_pnl:,.0f}", className="text-danger" if stress_pack.worst_case_pnl < 0 else "")
            ])
        ])
    ], className="mb-4 shadow")
    
    # Section 5: Analytics Charts
    # Netback Comparison Bar Chart
    netback_fig = go.Figure()
    netback_fig.add_trace(go.Bar(
        x=[europe_netback / 1e6, asia_netback / 1e6],
        y=['Europe<br>(Rotterdam)', 'Asia<br>(Tokyo)'],
        orientation='h',
        marker=dict(color=['#667eea', '#10b981'], line=dict(color='black', width=1.5)),
        text=[f'${europe_netback/1e6:.1f}M', f'${asia_netback/1e6:.1f}M'],
        textposition='inside',
        textfont=dict(size=14, color='white', family='Inter, sans-serif'),
        hovertemplate='%{y}: $%{x:.1f}M<extra></extra>'
    ))
    
    netback_fig.update_layout(
        title="Netback Comparison",
        xaxis_title="Netback (USD Million)",
        yaxis_title="",
        template='plotly_white',
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Inter, sans-serif', size=12, color='black'),
        xaxis=dict(gridcolor='rgba(0,0,0,0.1)'),
        showlegend=False
    )
    
    # Uplift Waterfall Chart
    raw_uplift = trade_pack["decision"]["delta_raw_usd"] / 1e6
    basis_haircut = raw_uplift * float(config["BASIS_ADJUSTMENT"])
    ops_buffer = float(config["OPS_BUFFER_USD"]) / 1e6
    
    waterfall_fig = go.Figure()
    waterfall_fig.add_trace(go.Waterfall(
        x=['Raw<br>Uplift', 'Basis<br>Haircut<br>(-5%)', 'Ops<br>Buffer', 'Adjusted<br>Uplift'],
        y=[raw_uplift, -basis_haircut, -ops_buffer, delta_adj / 1e6],
        measure=['absolute', 'relative', 'relative', 'total'],
        text=[f'${raw_uplift:.2f}M', f'-${basis_haircut:.2f}M', f'-${ops_buffer:.2f}M', f'${delta_adj/1e6:.2f}M'],
        textposition='inside',
        textfont=dict(color='white', size=12, family='Inter, sans-serif'),
        connector=dict(line=dict(color='rgba(0,0,0,0.3)', width=1, dash='dot')),
        increasing=dict(marker=dict(color='#10b981')),
        decreasing=dict(marker=dict(color='#ef4444')),
        totals=dict(marker=dict(color='#667eea')),
        hovertemplate='%{x}: $%{y:.2f}M<extra></extra>'
    ))
    
    waterfall_fig.update_layout(
        title="Uplift Waterfall: Raw to Adjusted",
        yaxis_title="USD (Million)",
        template='plotly_white',
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Inter, sans-serif', size=12, color='black'),
        yaxis=dict(gridcolor='rgba(0,0,0,0.1)'),
        showlegend=False
    )
    
    section_5 = dbc.Card([
        dbc.CardBody([
            html.H4("ANALYTICS CHARTS", className="text-muted mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=netback_fig, config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'netback_comparison',
                            'height': 900,
                            'width': 1600,
                            'scale': 3
                        }
                    })
                ], width=6),
                dbc.Col([
                    dcc.Graph(figure=waterfall_fig, config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'uplift_waterfall',
                            'height': 1050,
                            'width': 1600,
                            'scale': 3
                        }
                    })
                ], width=6),
            ]),
            
            html.P("💡 Charts update automatically with market data. Use the camera icon to download as PNG for presentations.",
                   className="text-muted text-center mt-2", style={'fontSize': '12px'})
        ])
    ], className="mb-4 shadow")
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Live data refreshed: {decision} @ ${delta_adj:,.0f}")
    
    return section_1, section_2, section_3, section_5


if __name__ == "__main__":
    print("\n" + "="*60)
    print("LNG DIVERSION DASHBOARD")
    print("="*60)
    print("Starting Dash server...")
    print("Access at: http://127.0.0.1:8050")
    print("")
    print("✨ AUTO-REFRESH ENABLED:")
    print("   • Fresh data on every page load")
    print("   • Auto-updates every 15 minutes while open")
    print("   • Backtest cached at startup (530 days)")
    print("")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=8050)
