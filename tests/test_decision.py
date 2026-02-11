#run test with: 'pytest tests/test_decision.py -s'

from engine.decision import decide_and_size

def test_decision_divert_when_uplift_large():
   res = decide_and_size(
       europe_netback_usd=100,
       asia_netback_usd=200,
       hedge_energy_mmbtu=100000,
       basis_haircut_pct=0.05,
       ops_buffer_usd=10,
       decision_buffer_usd=20,
   )
   #print(f"\n--- Test: DIVERT when uplift is large ---")
   #print(f"Raw uplift: ${res.delta_netback_raw_usd:,.2f}")
   #print(f"Adjusted uplift: ${res.delta_netback_adj_usd:,.2f}")
   #print(f"Decision: {res.decision}")
   #print(f"Hedge contracts: {res.lots_ttf} TTF, {res.lots_jkm} JKM")
   assert res.decision == "DIVERT"
   
def test_decision_keep_when_uplift_small():
   res = decide_and_size(
       europe_netback_usd=100,
       asia_netback_usd=110,
       hedge_energy_mmbtu=100000,
       basis_haircut_pct=0.05,
       ops_buffer_usd=10,
       decision_buffer_usd=20,
   )
   #print(f"\n--- Test: KEEP when uplift is small ---")
   #print(f"Raw uplift: ${res.delta_netback_raw_usd:,.2f}")
   #print(f"Adjusted uplift: ${res.delta_netback_adj_usd:,.2f}")
   #print(f"Decision: {res.decision}")
   #print(f"Hedge contracts: {res.lots_ttf} TTF, {res.lots_jkm} JKM")
   assert res.decision == "KEEP"