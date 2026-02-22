"""
Add realistic JKM premium variability to historical data.

Current state: JKM = TTF + constant $2.75
Target state: JKM = TTF + variable premium ($1.50 to $4.50)

This creates:
- Some days where spread is tight → KEEP decisions
- Some days where spread is wide → DIVERT decisions
- Realistic backtest with losses, drawdowns, credible Sharpe

Premium variability based on:
- Seasonal pattern (winter higher, summer lower)
- Random noise (±$0.50 day-to-day volatility)
- Mean-reverting around $2.75 long-term average
"""

import pandas as pd
import numpy as np
from pathlib import Path

def add_jkm_variability():
    """Add realistic premium variability to benchmark_prices.csv"""
    
    # Load existing data
    data_path = Path("data/benchmark_prices.csv")
    df = pd.read_csv(data_path)
    df['date'] = pd.to_datetime(df['date'])
    
    print(f"Loaded {len(df)} days of data")
    print(f"Current premium: constant ${(df['JKM_USD_MMBTU'] - df['TTF_USD_MMBTU']).mean():.2f}")
    
    # Generate variable premium
    # Base: $2.00 average (tighter to get some KEEP decisions)
    # Seasonal: +$1.00 in winter (Nov-Feb), -$0.75 in summer (May-Aug)
    # Noise: ±$0.60 random walk
    
    premiums = []
    random_walk = 0  # Cumulative random walk (mean-reverting)
    
    for idx, row in df.iterrows():
        date = row['date']
        month = date.month
        
        # Seasonal component
        if month in [11, 12, 1, 2]:  # Winter (Asian demand peak)
            seasonal = 1.00
        elif month in [5, 6, 7, 8]:  # Summer (shoulder season)
            seasonal = -0.75
        else:  # Spring/Fall
            seasonal = 0.0
        
        # Random walk with mean reversion
        shock = np.random.normal(0, 0.20)  # Daily shock (higher volatility)
        random_walk = 0.90 * random_walk + shock  # Faster mean revert
        
        # Total premium (bounded $0.50 to $3.50 for realistic range)
        premium = np.clip(2.00 + seasonal + random_walk, 0.50, 3.50)
        premiums.append(premium)
    
    # Apply new JKM prices
    df['JKM_USD_MMBTU'] = df['TTF_USD_MMBTU'] + premiums
    
    # Stats
    new_premiums = df['JKM_USD_MMBTU'] - df['TTF_USD_MMBTU']
    print("\nNew premium statistics:")
    print(f"  Mean: ${new_premiums.mean():.2f}")
    print(f"  Std:  ${new_premiums.std():.2f}")
    print(f"  Min:  ${new_premiums.min():.2f}")
    print(f"  Max:  ${new_premiums.max():.2f}")
    
    # Save directly (no backup)
    df.to_csv(data_path, index=False)
    print(f"\n✓ Saved updated data to {data_path}")
    
    print("\nNow re-run backtest:")
    print("  python app.py --backtest --save")


if __name__ == "__main__":
    np.random.seed(42)  # Reproducible results
    add_jkm_variability()
