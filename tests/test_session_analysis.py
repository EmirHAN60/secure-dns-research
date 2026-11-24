"""Small synthetic checks; fixtures are not research observations."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import session_analysis as analysis


class SessionAnalysisChecks(unittest.TestCase):
    def test_missing_session_does_not_read_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            planned={"session_id":"test","directory":"absent","scheduled_start_utc":"2026-11-22T20:00:00Z"}
            with patch.object(analysis,"read_jsonl",side_effect=AssertionError("Missing session raw file inspected")):
                status,data=analysis.load_session(root,planned,{})
            self.assertEqual(status["status"],"missing")
            self.assertIsNone(data)

    def test_running_session_does_not_read_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); session=root/"running";session.mkdir()
            (session/"environment.json").write_text(json.dumps({"status":"running","started_utc":"2026-11-22T20:00:00Z"}),encoding="utf-8")
            (session/"control_raw.jsonl").write_text("This is deliberately not JSON and must never be read.",encoding="utf-8")
            planned={"session_id":"test","directory":"running","scheduled_start_utc":"2026-11-22T20:00:00Z"}
            with patch.object(analysis,"read_jsonl",side_effect=AssertionError("Running session raw file inspected")):
                status,data=analysis.load_session(root,planned,{})
            self.assertEqual(status["status"],"running")
            self.assertIsNone(data)

    def test_negative_or_inconsistent_stages_surface_errors(self):
        self.assertTrue(analysis.check_stages({"elapsed_ms":-1,"valid":False}))
        row={"protocol":"udp_bound","valid":True,"pre_send_ms":1,"receive_ms":3,"transport_elapsed_ms":2,
             "post_bind_elapsed_ms":2.5,"validation_ms":.5,"bind_ready_ms":0,"socket_create_ms":0,"bind_wait_ms":0,"close_call_ms":0,"elapsed_ms":4}
        self.assertEqual(analysis.check_stages(row),[])
        row["transport_elapsed_ms"]=1
        self.assertTrue(analysis.check_stages(row))

    def test_magnitude_is_not_absolute_signed_median(self):
        stats=analysis.metric_stats([-3,-2,2,3])
        self.assertEqual(stats["median_delta_ms"],0)
        self.assertEqual(stats["median_abs_delta_ms"],2.5)
        rates=analysis.threshold_rates([{"delta_ms":x} for x in [-3,-2,2,3]],{},[2])[0]
        self.assertEqual(rates["fraction_abs_gt_threshold"],.5)
        self.assertEqual(rates["inside_band_count"],2)
        self.assertEqual(analysis.category(-2,2),"inside_threshold_band")


if __name__=="__main__":unittest.main()
