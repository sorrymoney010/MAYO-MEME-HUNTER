import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mayo_meme_hunter.research_collector import load_recent_mints, snapshot_for_mint

class SnapshotCollectorTests(unittest.TestCase):
    def test_snapshot_selects_most_liquid_matching_solana_pair(self):
        def fetcher(_mint):
            return [
                {"chainId":"solana","baseToken":{"address":"mint-x"},"liquidity":{"usd":"100"},
                 "priceUsd":"2","volume":{"m5":"50"},"txns":{"m5":{"buys":3,"sells":2}}},
                {"chainId":"solana","baseToken":{"address":"mint-x"},"liquidity":{"usd":"500"},
                 "priceUsd":"3","volume":{"m5":"200"},"txns":{"m5":{"buys":8,"sells":1}},
                 "priceChange":{"m5":"12"},"pairAddress":"pool-x","url":"https://example.invalid/pool"},
                {"chainId":"ethereum","baseToken":{"address":"mint-x"},"liquidity":{"usd":"99999"},
                 "priceUsd":"99"}
            ]
        row=snapshot_for_mint("mint-x",fetcher,observed_at=1000)
        self.assertEqual(row["price_usd"],3)
        self.assertEqual(row["liquidity_usd"],500)
        self.assertEqual(row["ts"],1000)
        self.assertIsNone(row["unique_buyers_5m"])
        self.assertFalse(row["execution_enabled"])

    def test_recent_mints_preserves_last_seen_order_and_caps(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"events.jsonl"
            rows=[{"mint":"a"},{"mint":"b"},{"mint":"a"},{"mint":"c"},{"mint":"d"}]
            path.write_text("".join(json.dumps(x)+"\n" for x in rows),encoding="utf-8")
            self.assertEqual(load_recent_mints(path,3),["a","c","d"])

if __name__=="__main__":
    unittest.main()
