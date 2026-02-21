"""
Download historical TTF and EUA price data from Yahoo Finance for backtesting

Run with: python tools/download_historical_data.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yfinance as yf
import pandas as pd
from datetime import datetime

# Download data from Jan 1, 2024 (when LNG shipping included in EU ETS)
end_date = datetime.now()
start_date = datetime(2024, 1, 1)

print("Downloading historical data from Yahoo Finance...")
print(f"Date range: {start_date.date()} to {end_date.date()}\n")

# Download TTF (European natural gas futures)
print("Fetching TTF (TTF=F)...")
ttf_data = yf.download("TTF=F", start=start_date, end=end_date, progress=False)

# Download EUA (Carbon allowances)
print("Fetching EUA (CO2.L)...")
eua_data = yf.download("CO2.L", start=start_date, end=end_date, progress=False)

# Merge on date
ttf_prices = ttf_data[["Close"]].copy()
ttf_prices.columns = ["TTF_USD_MMBTU"]

eua_prices = eua_data[["Close"]].copy()
eua_prices.columns = ["EUA_USD_PER_TCO2"]

# Combine
df = ttf_prices.join(eua_prices, how="inner")
df = df.dropna()

# Calculate JKM as TTF + premium (proxy)
JKM_PREMIUM = 2.75
df["JKM_USD_MMBTU"] = df["TTF_USD_MMBTU"] + JKM_PREMIUM

# Reset index to get date column
df = df.reset_index()
df["date"] = pd.to_datetime(df["Date"]).dt.date

# Save EUA separately before filtering columns
eua_series = df[["date", "EUA_USD_PER_TCO2"]].copy()

# Select columns for benchmark prices
df = df[["date", "TTF_USD_MMBTU", "JKM_USD_MMBTU"]]

# Save benchmark prices
output_path = Path("data/benchmark_prices.csv")
df.to_csv(output_path, index=False)
print(f"\n✓ Saved {len(df)} days to {output_path}")

# Create auxiliary series with constant proxies
aux_df = eua_series.copy()
aux_df["FREIGHT_USD_DAY"] = 85000
aux_df["FUEL_USD_PER_T"] = 747
aux_df = aux_df[["date", "FREIGHT_USD_DAY", "FUEL_USD_PER_T", "EUA_USD_PER_TCO2"]]

aux_output_path = Path("data/aux_series.csv")
aux_df.to_csv(aux_output_path, index=False)
print(f"✓ Saved {len(aux_df)} days to {aux_output_path}")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"Total days: {len(df)}")
print(f"\nTTF range: ${float(df['TTF_USD_MMBTU'].min()):.2f} - ${float(df['TTF_USD_MMBTU'].max()):.2f}")
print(f"EUA range: ${float(aux_df['EUA_USD_PER_TCO2'].min()):.2f} - ${float(aux_df['EUA_USD_PER_TCO2'].max()):.2f}")
print(f"JKM range: ${float(df['JKM_USD_MMBTU'].min()):.2f} - ${float(df['JKM_USD_MMBTU'].max()):.2f}")
print("="*60)
