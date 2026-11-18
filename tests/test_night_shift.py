import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from mayo_meme_hunter.night_shift import NightShiftConfig, ResearchStore, morning_report, orchestrate_candidate, run_once

class NightShiftTests(unittest.TestCase):
    def test_unknown_evidence_fails_closed_and_seven_roles_exist(self):
        r=orchestrate_candidate({"mint":"mint-demo","pair_url":"https://example.invalid/pair","missing_security_checks":["creator","bundle"],"all_blockers":["unknown"]})
        self.assertEqual(r["status"],"SKIP"); self.assertEqual(len(r["agents"]),7); self.assertFalse(r["execution_enabled"])
    def test_verified_evidence_only_allows_paper_review(self):
        r=orchestrate_candidate({"mint":"mint-demo","pair_url":"https://example.invalid/pair","developer_evidence":"fixture evidence","bundle_evidence":"fixture evidence","missing_security_checks":[],"all_blockers":[]})
        self.assertEqual(r["status"],"PASS_FOR_PAPER_REVIEW"); self.assertFalse(r["execution_enabled"])
    def test_source_failure_is_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=NightShiftConfig(Path(d)/"night.sqlite3")
            def broken(_): raise OSError("fixture source unavailable")
            r=run_once(cfg,broken); self.assertIn("source unavailable",r["source_error"]); self.assertFalse(r["execution_enabled"])
    def test_morning_report_reads_persistent_observations(self):
        with tempfile.TemporaryDirectory() as d:
            cfg=NightShiftConfig(Path(d)/"night.sqlite3"); ResearchStore(cfg.database).record({"observed_at":"2026-11-18T01:00:00+00:00","mint":"x","status":"SKIP","agents":[]})
            r=morning_report(cfg,"2026-11-18T00:00:00+00:00"); self.assertEqual(r["observations"],1); self.assertEqual(r["skipped"],1); self.assertIsNone(r["paper_pnl_usd"])
    def test_scheduler_interval_floor(self):
        with self.assertRaises(ValueError): NightShiftConfig(scan_interval_seconds=1)
if __name__=="__main__": unittest.main()
