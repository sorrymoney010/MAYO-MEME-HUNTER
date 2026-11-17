import os, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mayo_meme_hunter.execution import ExecutionGate, TradeIntent, TradeLimits

class Tests(unittest.TestCase):
    def setUp(self):
        self.gate = ExecutionGate()
        self.intent = TradeIntent("TOKEN", 10_000_000, 1000, True, True, True)
    def test_valid_policy(self):
        self.assertTrue(self.gate.validate_intent(self.intent, 1001))
    def test_unknown_security_blocks(self):
        bad = TradeIntent("TOKEN", 1, 1000, True, False, True)
        with self.assertRaises(ValueError): self.gate.validate_intent(bad, 1001)
    def test_stale_signal_blocks(self):
        with self.assertRaises(ValueError): self.gate.validate_intent(self.intent, 1020)
    def test_daily_cap_blocks(self):
        self.gate.spent_today_lamports = 195_000_000
        with self.assertRaises(ValueError): self.gate.validate_intent(self.intent, 1001)
    def test_live_is_hard_disabled_even_if_env_set(self):
        os.environ["MAYO_LIVE_TRADING_ENABLED"] = "true"
        self.assertFalse(self.gate.live_enabled)
        with self.assertRaises(PermissionError): self.gate.submit_signed("anything")
        os.environ.pop("MAYO_LIVE_TRADING_ENABLED", None)
    def test_hard_cap(self):
        with self.assertRaises(ValueError): TradeLimits(max_buy_lamports=60_000_000).validate()

if __name__ == "__main__": unittest.main()
