from engine.market_data import get_market_snapshot

def test_market_snapshot_proxy_jkm_from_ttf_plus_premium():
   cfg = {
       "TTF_USD_MMBTU": 35.69,
       "EUA_USD_PER_TCO2": 74.40,
       "JKM_PREMIUM_USD_PER_MMBTU": 2.75,
       "FREIGHT_USD_DAY": 85000,
       "FREIGHT_REGIME_MULTIPLIER": 1.0,
       "FUEL_USD_PER_T": 583,
   }
   snap = get_market_snapshot(cfg)
   assert snap.jkm_usd_mmbtu == 35.69 + 2.75
   assert snap.freight_usd_day == 85000
   
def test_market_snapshot_freight_regime_multiplier_applies():
   cfg = {
       "TTF_USD_MMBTU": 35.69,
       "EUA_USD_PER_TCO2": 74.40,
       "JKM_PREMIUM_USD_PER_MMBTU": 2.75,
       "FREIGHT_USD_DAY": 85000,
       "FREIGHT_REGIME_MULTIPLIER": 1.3,
       "FUEL_USD_PER_T": 583,
   }
   snap = get_market_snapshot(cfg)
   assert snap.freight_usd_day == 85000 * 1.3