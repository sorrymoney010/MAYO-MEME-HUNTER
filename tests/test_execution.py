import os,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from mayo_meme_hunter.execution import ExecutionGate,TradeIntent,TradeLimits
class Tests(unittest.TestCase):
 def setUp(self): self.g=ExecutionGate(); self.i=TradeIntent("TOKEN",10_000_000,1000,True,True,True)
 def test_valid(self): self.assertTrue(self.g.validate_intent(self.i,1001))
 def test_unknown_security_blocks(self):
  with self.assertRaises(ValueError): self.g.validate_intent(TradeIntent("T",1,1000,True,False,True),1001)
 def test_stale_blocks(self):
  with self.assertRaises(ValueError): self.g.validate_intent(self.i,1020)
 def test_daily_cap(self):
  self.g.spent_today_lamports=195_000_000
  with self.assertRaises(ValueError): self.g.validate_intent(self.i,1001)
 def test_live_off(self):
  os.environ.pop("MAYO_LIVE_TRADING_ENABLED",None)
  with self.assertRaises(PermissionError): self.g.execute_signed("signed","id",1)
 def test_hard_cap(self):
  with self.assertRaises(ValueError): TradeLimits(max_buy_lamports=60_000_000).validate()
if __name__=="__main__": unittest.main()
