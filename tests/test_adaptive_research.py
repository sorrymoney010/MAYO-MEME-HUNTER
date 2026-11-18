import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mayo_meme_hunter.research import ResearchStore

class AdaptiveResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ResearchStore(Path(self.tmp.name) / "research.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def test_ingest_is_idempotent_and_rejects_bad_rows(self):
        event = {"provider":"pumpportal","event_type":"create","mint":"mint-a","observed_at":1000,"signature":"sig-a"}
        self.assertEqual(self.store.ingest_events([event,event,{"mint":"","event_type":"create"}]),
                         {"inserted":1,"rejected":1})
        snap = {"mint":"mint-a","ts":1000,"price_usd":1.0,"source":"fixture"}
        self.assertEqual(self.store.ingest_snapshots([snap,snap,{"mint":"bad","ts":2,"price_usd":0}]),
                         {"inserted":1,"rejected":1})

    def test_forward_labels_exclude_pre_event_snapshots_and_capture_path(self):
        self.store.ingest_events([{"provider":"fixture","event_type":"create","mint":"mint-a","observed_at":1000,"signature":"s"}])
        self.store.ingest_snapshots([
            {"mint":"mint-a","ts":900,"price_usd":50,"source":"fixture"},
            {"mint":"mint-a","ts":1000,"price_usd":1,"source":"fixture"},
            {"mint":"mint-a","ts":1120,"price_usd":0.8,"source":"fixture"},
            {"mint":"mint-a","ts":1300,"price_usd":1.1,"source":"fixture"},
            {"mint":"mint-a","ts":1600,"price_usd":0.9,"source":"fixture"},
        ])
        result = self.store.build_labels(horizons=[5,10], max_lag_seconds=30)
        self.assertEqual(result, {"created":2,"skipped_incomplete":0})
        report = self.store.report()
        five, ten = report["outcomes_by_horizon"]
        self.assertAlmostEqual(five["avg_return"],10.0)
        self.assertAlmostEqual(five["avg_runup"],10.0)
        self.assertAlmostEqual(five["avg_drawdown"],-20.0)
        self.assertAlmostEqual(ten["avg_return"],-10.0)

    def test_missing_future_data_is_incomplete_not_zero_return(self):
        self.store.ingest_events([{"event_type":"create","mint":"mint-b","observed_at":100,"signature":"s"}])
        self.store.ingest_snapshots([{"mint":"mint-b","ts":100,"price_usd":2,"source":"fixture"}])
        self.assertEqual(self.store.build_labels(horizons=[5]), {"created":0,"skipped_incomplete":1})
        self.assertEqual(self.store.report()["counts"]["outcome_labels"],0)

    def test_rule_study_is_descriptive_and_execution_disabled(self):
        self.store.ingest_events([{"event_type":"create","mint":"mint-c","observed_at":100,"signature":"s"}])
        self.store.ingest_snapshots([
            {"mint":"mint-c","ts":100,"price_usd":1,"source":"fixture","liquidity_usd":20000,
             "volume_5m_usd":10000,"buys_5m":20,"sells_5m":5,"price_change_5m_pct":10},
            {"mint":"mint-c","ts":400,"price_usd":1.2,"source":"fixture"}
        ])
        self.store.build_labels(horizons=[5],max_lag_seconds=1)
        result=self.store.run_rule_study(5)
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["rules"][1]["sample_size"],1)
        self.assertEqual(result["rules"][1]["status"],"INSUFFICIENT_SAMPLE")

if __name__ == "__main__":
    unittest.main()
