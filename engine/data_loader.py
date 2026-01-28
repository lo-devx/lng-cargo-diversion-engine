"""
LNG Cargo Diversion Decision Engine

Data loading and validation module.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class MarketData:
    """Container for daily market data."""
    benchmark_prices: pd.DataFrame
    freight_rates: pd.DataFrame
    fuel_prices: pd.DataFrame


@dataclass
class StaticData:
    """Container for static/semi-static data."""
    routes: pd.DataFrame
    vessels: pd.DataFrame
    carbon_params: Dict[str, float]


@dataclass
class Config:
    """Container for configuration parameters."""
    decision_buffer_usd: float
    operational_risk_buffer_usd: float
    basis_adjustment_pct: float
    coverage_pct: float
    jkm_lot_mmbtu: float
    ttf_lot_mmbtu: float
    stress_spread_usd: float
    stress_freight_usd_per_day: float
    stress_eua_usd: float


class DataLoader:
    """Load and validate all input data."""
    
    LNG_DENSITY_T_PER_M3 = 0.45  # tonne per m3
    ENERGY_CONTENT_MMBTU_PER_T = 52  # MMBtu per tonne LNG
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
    
    def load_all(self) -> tuple[MarketData, StaticData, Config]:
        """Load all data and return containers."""
        market_data = self._load_market_data()
        static_data = self._load_static_data()
        config = self._load_config()
        
        self._validate_all(market_data, static_data, config)
        
        return market_data, static_data, config
    
    def _load_market_data(self) -> MarketData:
        """Load daily market data CSVs."""
        benchmark_prices = pd.read_csv(
            self.data_dir / "benchmark_prices.csv",
            parse_dates=["date"]
        )
        freight_rates = pd.read_csv(
            self.data_dir / "freight_rates.csv",
            parse_dates=["date"]
        )
        fuel_prices = pd.read_csv(
            self.data_dir / "fuel_prices.csv",
            parse_dates=["date"]
        )
        
        return MarketData(
            benchmark_prices=benchmark_prices,
            freight_rates=freight_rates,
            fuel_prices=fuel_prices
        )
    
    def _load_static_data(self) -> StaticData:
        """Load static/semi-static data."""
        routes = pd.read_csv(self.data_dir / "routes.csv")
        vessels = pd.read_csv(self.data_dir / "vessels.csv")
        
        carbon_params_df = pd.read_csv(self.data_dir / "carbon_params.csv")
        carbon_params = dict(zip(carbon_params_df["param"], carbon_params_df["value"]))
        
        return StaticData(
            routes=routes,
            vessels=vessels,
            carbon_params=carbon_params
        )
    
    def _load_config(self) -> Config:
        """Load configuration parameters."""
        config_df = pd.read_csv(self.data_dir / "config.csv")
        config_dict = dict(zip(config_df["param"], config_df["value"]))
        
        return Config(
            decision_buffer_usd=config_dict["DECISION_BUFFER_USD"],
            operational_risk_buffer_usd=config_dict["OPERATIONAL_RISK_BUFFER_USD"],
            basis_adjustment_pct=config_dict["BASIS_ADJUSTMENT_PCT"],
            coverage_pct=config_dict["COVERAGE_PCT"],
            jkm_lot_mmbtu=config_dict["JKM_LOT_MMBTU"],
            ttf_lot_mmbtu=config_dict["TTF_LOT_MMBTU"],
            stress_spread_usd=config_dict["STRESS_SPREAD_USD"],
            stress_freight_usd_per_day=config_dict["STRESS_FREIGHT_USD_PER_DAY"],
            stress_eua_usd=config_dict["STRESS_EUA_USD"]
        )
    
    def _validate_all(self, market_data: MarketData, static_data: StaticData, config: Config):
        """Run all validation checks."""
        # Check for duplicate dates
        self._check_no_duplicate_dates(market_data.benchmark_prices, "benchmark_prices")
        self._check_no_duplicate_dates(market_data.freight_rates, "freight_rates")
        self._check_no_duplicate_dates(market_data.fuel_prices, "fuel_prices")
        
        # Check for negative values
        self._check_no_negative_values(market_data.benchmark_prices, ["TTF", "JKM"], "benchmark_prices")
        self._check_no_negative_values(market_data.freight_rates, ["TFDE_USD_day", "MEGI_USD_day"], "freight_rates")
        self._check_no_negative_values(market_data.fuel_prices, ["VLSFO_USD_per_t", "LNG_USD_per_t"], "fuel_prices")
        self._check_no_negative_values(static_data.routes, ["distance_nm"], "routes")
        self._check_no_negative_values(static_data.vessels, ["laden_speed_kn", "ballast_speed_kn"], "vessels")
        
        # Check config bounds
        if not 0 <= config.basis_adjustment_pct <= 1:
            raise ValueError("BASIS_ADJUSTMENT_PCT must be between 0 and 1")
        if not 0 <= config.coverage_pct <= 1:
            raise ValueError("COVERAGE_PCT must be between 0 and 1")
        
        # Check vessel classes match freight rates
        vessel_classes = set(static_data.vessels["vessel_class"])
        expected_classes = {"TFDE", "MEGI"}
        if not vessel_classes.issubset(expected_classes):
            raise ValueError(f"vessel_class must be TFDE or MEGI, got {vessel_classes}")
        
        # Check required carbon params
        required_carbon_params = [
            "EUA_price_USD_per_t",
            "CO2_factor_VLSFO_tCO2_per_t_fuel",
            "CO2_factor_LNG_tCO2_per_t_fuel"
        ]
        for param in required_carbon_params:
            if param not in static_data.carbon_params:
                raise ValueError(f"Missing required carbon param: {param}")
    
    def _check_no_duplicate_dates(self, df: pd.DataFrame, name: str):
        """Check that there are no duplicate dates."""
        if df["date"].duplicated().any():
            raise ValueError(f"Duplicate dates found in {name}")
    
    def _check_no_negative_values(self, df: pd.DataFrame, columns: list, name: str):
        """Check that specified columns have no negative values."""
        for col in columns:
            if (df[col] < 0).any():
                raise ValueError(f"Negative values found in {name}.{col}")
