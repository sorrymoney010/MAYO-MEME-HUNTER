import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mayo_meme_hunter.core import Config, PaperEngine, Snapshot, evaluate
from mayo_meme_hunter.scanner import _as_snapshot
from mayo_meme_hunter.wallets import analyze_wallet_events

BASE = dict(
    ts=1794873600, mint="DEMO_ONLY", symbol="DEMO", price_usd=1.0,
    age_minutes=5, liquidity_usd=120000, volume_5m_usd=60000,
    buys_5m=100, sells_5m=30, unique_buyers_5m=120,
    top10_pct=20, creator_pct=2, mint_authority_disabled=True,
    freeze_authority_disabled=True, token_program_safe=True,
    sell_route_available=True, suspicious_clusters=False,
    price_change_5m_pct=12,
)


def tick(ts, price=1.0, **changes):
    return Snapshot(**(BASE | {"ts": ts, "price_usd": price} | changes))


class SafetyTests(unittest.TestCase):
    def test_known_good_candidate(self):
        self.assertEqual(evaluate(tick(1), Config())["decision"], "CANDIDATE")

    def test_unknown_fields_fail_closed(self):
        self.assertEqual(evaluate(replace(tick(1), sell_route_available=None), Config())["decision"], "REJECT")
        self.assertEqual(evaluate(replace(tick(1), token_program_safe=None), Config())["decision"], "REJECT")
        self.assertEqual(evaluate(replace(tick(1), top10_pct=None), Config())["decision"], "REJECT")

    def test_honeypot_and_concentration_block(self):
        self.assertEqual(evaluate(replace(tick(1), suspicious_clusters=True), Config())["decision"], "REJECT")
        self.assertEqual(evaluate(replace(tick(1), top10_pct=70), Config())["decision"], "REJECT")

    def test_dex_feed_does_not_forge_safety(self):
        p = {"chainId": "solana", "baseToken": {"symbol": "ABC"}, "priceUsd": "0.1",
             "liquidity": {"usd": 100000}, "txns": {"m5": {"buys": 200, "sells": 40}},
             "volume": {"m5": 100000}, "priceChange": {"m5": 15}}
        s = _as_snapshot(p, "abc", 1794873600000)
        self.assertIsNone(s.sell_route_available)
        self.assertEqual(evaluate(s, Config())["decision"], "REJECT")

    def test_config_cannot_relax_risk_beyond_ceiling(self):
        with self.assertRaises(ValueError):
            Config(risk_per_trade=.1)


class ReplayTests(unittest.TestCase):
    def test_signal_enters_on_next_tick_not_same_tick(self):
        e = PaperEngine()
        e.process(tick(1794873600))
        self.assertEqual(len(e.positions), 0)
        e.process(tick(1794873610, 1.01))
        self.assertEqual(len(e.positions), 1)
        self.assertEqual(e.trades, [])

    def test_take_profit_and_net_fees(self):
        e = PaperEngine()
        e.process(tick(1794873600))
        e.process(tick(1794873610, 1.0))
        e.process(tick(1794873620, 1.30))
        self.assertEqual(len(e.trades), 1)
        self.assertEqual(e.trades[0]["reason"], "take profit")
        self.assertGreater(e.trades[0]["pnl_usd"], 0)
        self.assertLess(e.trades[0]["pnl_usd"], 3.0)  # Costs matter

    def test_loss_stop(self):
        e = PaperEngine()
        e.process(tick(1794873600))
        e.process(tick(1794873610))
        e.process(tick(1794873620, .70))
        self.assertEqual(e.trades[0]["reason"], "stop")
        self.assertLess(e.trades[0]["pnl_usd"], 0)

    def test_unavailable_sell_route_never_fakes_exit(self):
        e = PaperEngine()
        e.process(tick(1794873600))
        e.process(tick(1794873610))
        e.process(tick(1794873620, .60, sell_route_available=False))
        self.assertEqual(len(e.trades), 0)
        self.assertEqual(e.report()["trapped_positions"], 1)
        self.assertTrue(any(d["action"] == "EXIT_BLOCKED" for d in e.decisions))

    def test_duplicate_timestamp_rejected(self):
        e = PaperEngine()
        e.process(tick(1794873600))
        with self.assertRaises(ValueError):
            e.process(tick(1794873600))

    def test_no_live_orders(self):
        e = PaperEngine()
        self.assertFalse(e.report()["live_orders_enabled"])
        self.assertFalse(e.report()["research_gate_passed"])

    def test_entry_blocked_after_daily_loss(self):
        e = PaperEngine()
        e.process(tick(1794873600))
        e.process(tick(1794873610))
        e.process(tick(1794873620, .01))
        self.assertTrue(e.daily_halted)
        self.assertEqual(len(e.positions), 0)


class WalletTests(unittest.TestCase):
    def test_copy_friction_reduces_pnl(self):
        rows = [{"ts": 1, "wallet": "A", "mint": "X", "side": "buy", "qty": 100, "price_usd": 1},
                {"ts": 2, "wallet": "A", "mint": "X", "side": "sell", "qty": 100, "price_usd": 1.1}]
        result = analyze_wallet_events(rows)[0]
        self.assertAlmostEqual(result["copy_adjusted_pnl_usd"], 5.8)
        self.assertFalse(result["watch_eligible"])

    def test_unmatched_sell_not_profitable(self):
        result = analyze_wallet_events([{"ts": 1, "wallet": "A", "mint": "X", "side": "sell",
                                         "qty": 100, "price_usd": 2}])[0]
        self.assertEqual(result["matched_lots"], 0)
        self.assertEqual(result["unmatched_or_invalid_events"], 1)


if __name__ == "__main__":
    unittest.main()
