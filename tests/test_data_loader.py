# Run with: pytest tests/test_data_loader.py -s

from engine.data_loader import load_routes, load_vessels, load_carbon_params, load_config

def test_load_routes():
    routes = load_routes()
    print(f"\n✓ Loaded {len(routes)} routes")
    print(routes)
    assert len(routes) > 0
    assert "load_port" in routes.columns
    assert "discharge_port" in routes.columns
    assert "distance_nm" in routes.columns

def test_load_vessels():
    vessels = load_vessels()
    print(f"\n✓ Loaded {len(vessels)} vessel classes")
    print(vessels)
    assert len(vessels) > 0
    assert "vessel_class" in vessels.columns
    assert "cargo_capacity_m3" in vessels.columns

def test_load_carbon_params():
    carbon = load_carbon_params()
    print(f"\n✓ Loaded carbon params: {carbon}")
    assert isinstance(carbon, dict)
    assert len(carbon) > 0

def test_load_config():
    config = load_config()
    print(f"\n✓ Loaded config: {config}")
    assert isinstance(config, dict)
    assert len(config) > 0
