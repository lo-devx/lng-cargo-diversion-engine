"""
LNG Cargo Diversion Decision Engine

Data loading and validation module.
"""

import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Dict
from engine.validation import validate_config

DATA_DIR = Path("data")


@dataclass
class MarketData:
    """Market data snapshot."""
    ttf_price: float
    jkm_price: float
    freight_rate: float
    fuel_price: float
    eua_price: float


@dataclass
class StaticData:
    """Static reference data."""
    routes: pd.DataFrame
    vessels: pd.DataFrame
    carbon_params: Dict[str, float]


@dataclass
class Config:
    """Configuration parameters."""
    basis_haircut_pct: float
    ops_buffer_usd: float
    decision_buffer_usd: float


class DataLoader:
    """Load all data from CSV files."""
    
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
    
    def load_routes(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "routes.csv")
    
    def load_vessels(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "vessels.csv")
    
    def load_carbon_params(self) -> Dict[str, float]:
        df = pd.read_csv(self.data_dir / "carbon_params.csv")
        return dict(zip(df["param"], df["value"]))
    
    def load_config(self) -> Config:
        df = pd.read_csv(self.data_dir / "config.csv")
        params = dict(zip(df["param"], df["value"]))
        validate_config(params)
        return Config(**params)
    
    def load_static_data(self) -> StaticData:
        """Load all static data."""
        return StaticData(
            routes=self.load_routes(),
            vessels=self.load_vessels(),
            carbon_params=self.load_carbon_params()
        )

