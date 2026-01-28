"""
LNG Cargo Diversion Decision Engine

Netback calculation module.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import pandas as pd


# Constants
LNG_DENSITY_T_PER_M3 = 0.45  # tonne per m3
ENERGY_CONTENT_MMBTU_PER_T = 52  # MMBtu per tonne LNG
HOURS_PER_DAY = 24


@dataclass
class VoyageDetails:
    """Details of a voyage calculation."""
    distance_nm: float
    voyage_days: float
    boil_off_m3: float
    delivered_cargo_m3: float
    delivered_energy_mmbtu: float
    fuel_consumed_tonnes: float
    fuel_cost_usd: float
    time_charter_cost_usd: float
    carbon_cost_usd: float
    total_voyage_cost_usd: float


@dataclass
class NetbackResult:
    """Result of netback calculation for a destination."""
    destination: str
    price_usd_mmbtu: float
    delivered_energy_mmbtu: float
    revenue_usd: float
    voyage_cost_usd: float
    carbon_cost_usd: float
    netback_usd: float
    voyage_details: VoyageDetails


class NetbackCalculator:
    """Calculate netback for Europe and Asia destinations."""
    
    def __init__(
        self,
        routes: pd.DataFrame,
        vessels: pd.DataFrame,
        carbon_params: Dict[str, float]
    ):
        self.routes = routes
        self.vessels = vessels
        self.carbon_params = carbon_params
    
    def calculate_voyage(
        self,
        load_port: str,
        discharge_port: str,
        vessel_class: str,
        cargo_capacity_m3: float,
        freight_rate_usd_day: float,
        fuel_price_usd_t: float,
        eua_price_usd_t: float,
        fuel_type: str = "VLSFO"
    ) -> VoyageDetails:
        """Calculate voyage costs and details."""
        # Get route distance
        route = self.routes[
            (self.routes["load_port"] == load_port) &
            (self.routes["discharge_port"] == discharge_port)
        ]
        if route.empty:
            raise ValueError(f"Route not found: {load_port} -> {discharge_port}")
        
        distance_nm = route["distance_nm"].values[0]
        
        # Get vessel parameters
        vessel = self.vessels[self.vessels["vessel_class"] == vessel_class]
        if vessel.empty:
            raise ValueError(f"Vessel class not found: {vessel_class}")
        
        vessel = vessel.iloc[0]
        laden_speed_kn = vessel["laden_speed_kn"]
        boil_off_pct_per_day = vessel["boil_off_pct_per_day"]
        fuel_consumption_tpd = vessel["fuel_consumption_tpd_laden"]
        
        # Calculate voyage time (laden leg only for simplicity)
        voyage_days = distance_nm / (laden_speed_kn * HOURS_PER_DAY)
        
        # Calculate boil-off
        # Boil-off percentage is per day, so total boil-off = cargo * rate * days
        boil_off_m3 = cargo_capacity_m3 * (boil_off_pct_per_day / 100) * voyage_days
        delivered_cargo_m3 = cargo_capacity_m3 - boil_off_m3
        
        # Convert to energy
        delivered_cargo_tonnes = delivered_cargo_m3 * LNG_DENSITY_T_PER_M3
        delivered_energy_mmbtu = delivered_cargo_tonnes * ENERGY_CONTENT_MMBTU_PER_T
        
        # Fuel costs
        fuel_consumed_tonnes = fuel_consumption_tpd * voyage_days
        fuel_cost_usd = fuel_consumed_tonnes * fuel_price_usd_t
        
        # Time charter cost
        time_charter_cost_usd = freight_rate_usd_day * voyage_days
        
        # Carbon cost
        if fuel_type == "VLSFO":
            co2_factor = self.carbon_params["CO2_factor_VLSFO_tCO2_per_t_fuel"]
        else:
            co2_factor = self.carbon_params["CO2_factor_LNG_tCO2_per_t_fuel"]
        
        carbon_emissions_tco2 = fuel_consumed_tonnes * co2_factor
        carbon_cost_usd = carbon_emissions_tco2 * eua_price_usd_t
        
        # Total voyage cost
        total_voyage_cost_usd = fuel_cost_usd + time_charter_cost_usd + carbon_cost_usd
        
        return VoyageDetails(
            distance_nm=distance_nm,
            voyage_days=voyage_days,
            boil_off_m3=boil_off_m3,
            delivered_cargo_m3=delivered_cargo_m3,
            delivered_energy_mmbtu=delivered_energy_mmbtu,
            fuel_consumed_tonnes=fuel_consumed_tonnes,
            fuel_cost_usd=fuel_cost_usd,
            time_charter_cost_usd=time_charter_cost_usd,
            carbon_cost_usd=carbon_cost_usd,
            total_voyage_cost_usd=total_voyage_cost_usd
        )
    
    def calculate_netback(
        self,
        destination: str,
        destination_price_usd_mmbtu: float,
        voyage_details: VoyageDetails
    ) -> NetbackResult:
        """Calculate netback for a destination."""
        # Revenue = Price × Delivered Energy
        revenue_usd = destination_price_usd_mmbtu * voyage_details.delivered_energy_mmbtu
        
        # Netback = Revenue - VoyageCost - CarbonCost
        # Note: Carbon cost is already included in voyage_cost
        netback_usd = revenue_usd - voyage_details.total_voyage_cost_usd
        
        return NetbackResult(
            destination=destination,
            price_usd_mmbtu=destination_price_usd_mmbtu,
            delivered_energy_mmbtu=voyage_details.delivered_energy_mmbtu,
            revenue_usd=revenue_usd,
            voyage_cost_usd=voyage_details.total_voyage_cost_usd - voyage_details.carbon_cost_usd,
            carbon_cost_usd=voyage_details.carbon_cost_usd,
            netback_usd=netback_usd,
            voyage_details=voyage_details
        )
    
    def compare_netbacks(
        self,
        load_port: str,
        europe_port: str,
        asia_port: str,
        vessel_class: str,
        cargo_capacity_m3: float,
        ttf_price: float,
        jkm_price: float,
        freight_rate_usd_day: float,
        fuel_price_usd_t: float,
        eua_price_usd_t: float
    ) -> tuple[NetbackResult, NetbackResult]:
        """Calculate and compare netbacks for Europe and Asia."""
        # Europe voyage
        europe_voyage = self.calculate_voyage(
            load_port=load_port,
            discharge_port=europe_port,
            vessel_class=vessel_class,
            cargo_capacity_m3=cargo_capacity_m3,
            freight_rate_usd_day=freight_rate_usd_day,
            fuel_price_usd_t=fuel_price_usd_t,
            eua_price_usd_t=eua_price_usd_t
        )
        europe_netback = self.calculate_netback(
            destination="Europe",
            destination_price_usd_mmbtu=ttf_price,
            voyage_details=europe_voyage
        )
        
        # Asia voyage
        asia_voyage = self.calculate_voyage(
            load_port=load_port,
            discharge_port=asia_port,
            vessel_class=vessel_class,
            cargo_capacity_m3=cargo_capacity_m3,
            freight_rate_usd_day=freight_rate_usd_day,
            fuel_price_usd_t=fuel_price_usd_t,
            eua_price_usd_t=eua_price_usd_t
        )
        asia_netback = self.calculate_netback(
            destination="Asia",
            destination_price_usd_mmbtu=jkm_price,
            voyage_details=asia_voyage
        )
        
        return europe_netback, asia_netback
