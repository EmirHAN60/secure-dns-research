"""In-memory statistics checks; synthetic values never enter research data."""
from pathlib import Path
from fractions import Fraction
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import repeatability_analysis as a


class RepeatabilityStatistics(unittest.TestCase):
    def test_declared_inverse_cdf_tie(self):
        observations=[({"x":0},Fraction(1,2)),({"x":10},Fraction(1,2))]
        self.assertEqual(a.weighted_quantile(observations,"x",Fraction(1,2)),0)

    def example(self):
        plan={"design":{"windows":2,"domains":["example.com"],"step_ms":100},"thresholds_ms":[2]}
        spec={"positions":["1-2"],"lag_ms_inclusive":[75,125]}
        pairs=[]
        for window in (1,2):
            for cls in a.CLASSES:
                for index in range(4 if window==1 and cls=="DU" else 1):
                    value=10 if window==1 else 0
                    pairs.append({"provider":"cloudflare","flow_condition":"repeat_flow","window":window,"domain":"example.com","position_pair":"1-2",
                                  "position_separation":1,"pair_class":cls,"pair_valid":True,"actual_start_lag_ms":100,"signed_delta_ms":value,"abs_delta_ms":value,"block_id":f"{cls}-{index}"})
        return plan,spec,pairs

    def test_equal_window_weight_despite_unequal_pair_counts(self):
        plan,spec,pairs=self.example()
        rows,rates,_=a.common_estimates(pairs,plan,spec,"test","cloudflare","repeat_flow","test")
        du=next(r for r in rows if r["pair_class"]=="DU")
        rate=next(r for r in rates if r["pair_class"]=="DU")
        self.assertEqual(du["pair_count"],5)
        self.assertEqual(du["weighted_median_abs_delta_ms"],0)
        self.assertEqual(rate["weighted_fraction_abs_gt_threshold"],.5)

    def test_no_fallback_when_one_window_lacks_common_overlap(self):
        plan,spec,pairs=self.example()
        pairs=[p for p in pairs if not(p["window"]==2 and p["pair_class"]=="DD")]
        rows,rates,_=a.common_estimates(pairs,plan,spec,"test","cloudflare","repeat_flow","test")
        self.assertTrue(all(r["estimate_status"]=="insufficient_common_lag_overlap" for r in rows))
        self.assertTrue(all(r["weighted_median_abs_delta_ms"] is None for r in rows))
        self.assertEqual(rates,[])

    def test_common_cells_have_equal_mass_with_unequal_observation_counts(self):
        plan,spec,_=self.example();plan["design"]["windows"]=1;spec["positions"]=["1-2","2-3"]
        pairs=[]
        for position,value in (("1-2",10),("2-3",0)):
            for cls in a.CLASSES:
                for index in range(4 if position=="1-2" and cls=="DU" else 1):
                    pairs.append({"provider":"cloudflare","flow_condition":"repeat_flow","window":1,"domain":"example.com","position_pair":position,
                                  "position_separation":1,"pair_class":cls,"pair_valid":True,"actual_start_lag_ms":100,"signed_delta_ms":value,"abs_delta_ms":value,"block_id":f"{position}-{cls}-{index}"})
        rows,rates,_=a.common_estimates(pairs,plan,spec,"test","cloudflare","repeat_flow","test")
        self.assertTrue(all(r["weighted_median_abs_delta_ms"]==0 for r in rows))
        self.assertTrue(all(r["weighted_fraction_abs_gt_threshold"]==.5 for r in rates))

    def test_threshold_uses_strict_exceedance(self):
        plan,spec,pairs=self.example()
        for p in pairs:p.update(signed_delta_ms=2,abs_delta_ms=2)
        _,rates,_=a.common_estimates(pairs,plan,spec,"test","cloudflare","repeat_flow","test")
        self.assertTrue(all(r["weighted_fraction_abs_gt_threshold"]==0 for r in rates))

    def test_cross_mode_orientation_and_failed_pairs(self):
        rows=[]
        for pos,(protocol,latency) in enumerate(zip(["doh_warm","udp_bound","doh_warm","udp_bound"],[10,4,12,6]),1):
            start=(pos-1)*100
            rows.append({"phase":"measure","window":1,"block_id":"test","provider":"cloudflare","domain":"example.com","flow_condition":"repeat_flow","sequence":"DUDU",
                         "position":pos,"protocol":protocol,"valid":True,"elapsed_ms":latency,"actual_start_monotonic_ms":start,"measurement_end_monotonic_ms":start+latency,
                         "flow_id":protocol,"flow_index":0,"start_lateness_ms":0})
        pairs=a.pair_observations(rows,"test")
        self.assertEqual(len(pairs),6)
        first=next(p for p in pairs if p["position_pair"]=="1-2")
        self.assertEqual(first["pair_class"],"DU")
        self.assertEqual(first["signed_delta_ms"],6)
        rows[0]["valid"]=False;rows[0]["error"]="Synthetic timeout marker"
        pairs=a.pair_observations(rows,"test")
        self.assertEqual(sum(p["pair_valid"] for p in pairs),3)
        self.assertTrue(all(p["signed_delta_ms"] is None for p in pairs if not p["pair_valid"]))

    def test_running_run_does_not_read_raw_outcomes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=root/"data";data.mkdir()
            (data/"environment.json").write_text(json.dumps({"status":"running","started_utc":"2026-11-23T21:00:00Z"}),encoding="utf-8")
            with patch.object(a,"read_rows",side_effect=AssertionError("Running run outcomes inspected")):
                status,summary,pairs=a.run_analysis(root,{"run_id":"test","directory":"data"},{},{})
            self.assertEqual(status["status"],"running")
            self.assertIsNone(summary)
            self.assertIsNone(pairs)


if __name__=="__main__":unittest.main()
