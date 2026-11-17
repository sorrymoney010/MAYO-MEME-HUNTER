import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from mayo_meme_hunter.stream import normalize_event
from mayo_meme_hunter.rpc import SolanaRPC,TOKEN_PROGRAM,TOKEN_2022_PROGRAM
class StreamTests(unittest.TestCase):
 def test_create(self):
  x=normalize_event({"txType":"create","mint":"MINT","symbol":"T"},123)
  self.assertEqual(x["event_type"],"create"); self.assertEqual(x["observed_at"],123); self.assertFalse(x["execution_enabled"])
 def test_migration_alias(self):
  self.assertEqual(normalize_event({"txType":"migrate","mint":"M","pool":"P"})["event_type"],"migration")
 def test_migration_event(self):
  self.assertEqual(normalize_event({"txType":"migration","mint":"M"})["event_type"],"migration")
 def test_trade_ignored(self): self.assertIsNone(normalize_event({"txType":"buy","mint":"M"}))
 def test_missing_mint_ignored(self): self.assertIsNone(normalize_event({"txType":"create"}))
class RPCTests(unittest.TestCase):
 def test_missing_mint_unknown(self):
  rpc=SolanaRPC("https://invalid.example"); rpc.call=lambda method,params:{"value":None}
  self.assertEqual(rpc.inspect_mint("M")["status"],"UNKNOWN")
 def test_program_ids_differ(self): self.assertNotEqual(TOKEN_PROGRAM,TOKEN_2022_PROGRAM)
if __name__=="__main__": unittest.main()
