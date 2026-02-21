"""
LNG Cargo Diversion Decision Engine

Backtesting module - Analyzes historical trading performance

This module takes a list of historical decision results (from app.py's backtest loop)
and calculates performance metrics to validate the decision rule.

Key responsibilities:
- Calculate hit rate (% of days triggering DIVERT)
- Compute average and total uplift from triggered trades
- Build equity curve (cumulative P&L over time)
- Calculate max drawdown (worst peak-to-trough decline)
- Compute Sharpe ratio (annualized risk-adjusted returns)

Called by: app.py when --backtest flag is used
Input: List of decision results with dates, decisions, and netbacks
Output: BacktestResult with metrics and DataFrames for equity curve and trade history

Example:
    backtester = Backtester()
    backtest_result = backtester.run_backtest(results)
    print(backtest_result.metrics.hit_rate)  # 1.0 = 100% hit rate
"""

from dataclasses import dataclass
from typing import List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from .decision import DecisionResult


@dataclass
class BacktestMetrics:
    """Backtest performance metrics."""
    total_observations: int
    triggered_trades: int
    hit_rate: float  # Trigger frequency
    average_uplift_usd: float  # Average delta netback when triggered
    total_uplift_usd: float
    max_drawdown_usd: float
    sharpe_ratio: Optional[float]  # If enough data points


@dataclass
class BacktestResult:
    """Complete backtest result."""
    metrics: BacktestMetrics
    equity_curve: pd.DataFrame  # date, cumulative_pnl
    decision_history: pd.DataFrame  # Full history of decisions


class Backtester:
    """Backtest the decision engine on historical data."""
    
    def __init__(self):
        pass
    
    def run_backtest(self, results: List[DecisionResult]) -> BacktestResult:
        """
        Run backtest on a list of decision results.
        
        Assumes results are in chronological order.
        """
        if not results:
            raise ValueError("No results to backtest")
        
        # Build decision history DataFrame
        history_data = []
        for r in results:
            history_data.append({
                "date": r.date,
                "decision": r.decision,
                "delta_netback_raw_usd": r.delta_netback_raw_usd,
                "delta_netback_adj_usd": r.delta_netback_adj_usd,
                "netback_europe_usd": r.europe_netback.netback_usd,
                "netback_asia_usd": r.asia_netback.netback_usd,
                "triggered": 1 if r.decision == "DIVERT" else 0
            })
        
        decision_history = pd.DataFrame(history_data)
        decision_history = decision_history.sort_values("date").reset_index(drop=True)
        
        # Calculate metrics
        total_obs = len(decision_history)
        triggered = decision_history["triggered"].sum()
        hit_rate = triggered / total_obs if total_obs > 0 else 0.0
        
        # Average uplift when triggered
        triggered_rows = decision_history[decision_history["triggered"] == 1]
        if len(triggered_rows) > 0:
            average_uplift = triggered_rows["delta_netback_adj_usd"].mean()
            total_uplift = triggered_rows["delta_netback_adj_usd"].sum()
        else:
            average_uplift = 0.0
            total_uplift = 0.0
        
        # Build equity curve (cumulative P&L from diversions)
        decision_history["pnl"] = decision_history.apply(
            lambda row: row["delta_netback_adj_usd"] if row["triggered"] == 1 else 0,
            axis=1
        )
        decision_history["cumulative_pnl"] = decision_history["pnl"].cumsum()
        
        equity_curve = decision_history[["date", "cumulative_pnl"]].copy()
        
        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown(decision_history["cumulative_pnl"])
        
        # Calculate Sharpe ratio (if enough data)
        sharpe = None
        if len(decision_history) >= 5:
            returns = decision_history["pnl"]
            if returns.std() > 0:
                sharpe = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized
        
        metrics = BacktestMetrics(
            total_observations=total_obs,
            triggered_trades=int(triggered),
            hit_rate=hit_rate,
            average_uplift_usd=average_uplift,
            total_uplift_usd=total_uplift,
            max_drawdown_usd=max_drawdown,
            sharpe_ratio=sharpe
        )
        
        return BacktestResult(
            metrics=metrics,
            equity_curve=equity_curve,
            decision_history=decision_history
        )
    
    def _calculate_max_drawdown(self, cumulative_pnl: pd.Series) -> float:
        """Calculate maximum drawdown from cumulative P&L series."""
        if len(cumulative_pnl) == 0:
            return 0.0
        
        # Running maximum
        running_max = cumulative_pnl.cummax()
        
        # Drawdown at each point
        drawdown = running_max - cumulative_pnl
        
        # Maximum drawdown
        return drawdown.max()
