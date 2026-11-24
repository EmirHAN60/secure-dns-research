"""Research-property tests. Tiny artificial fixtures here are never study data."""
from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("dns_analysis", ROOT / "scripts/analyze.py")
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def lookup(mode, value=1.0, valid=True, **changes):
    row = dict(provider="cloudflare", domain="example.com", window=1, rep=1,
               protocol=mode, elapsed_ms=value, valid=valid, phase="measure")
    row.update(changes)
    return row


class AnalysisProperties(unittest.TestCase):
    def test_pair_before_aggregate_has_a_distinct_answer(self):
        rows = []
        for rep, baseline, comparison in ((1, 1, 2), (2, 100, 1000), (3, 101, 102)):
            rows.extend((lookup("udp", baseline, rep=rep), lookup("doh_fresh", comparison, rep=rep)))
        overall, _, _, _ = A.analyze_pairs(rows, "lookup")
        effect = next(r for r in overall if r["comparison"] == "doh_fresh")
        self.assertEqual(effect["complete_pairs"], 3)
        self.assertEqual(effect["median_delta_ms"], 1)
        marginal = A.describe([2, 1000, 102])["median_ms"] - A.describe([1, 100, 101])["median_ms"]
        self.assertEqual(marginal, 2)

    def test_failures_and_missing_comparisons_are_not_imputed(self):
        blocks = [
            dict(window=1, domain="x", rep=1, modes={"udp": lookup("udp", 10), "doh_fresh": lookup("doh_fresh", 13)}),
            dict(window=1, domain="x", rep=2, modes={"udp": lookup("udp", 10), "doh_fresh": lookup("doh_fresh", valid=False)}),
            dict(window=1, domain="x", rep=3, modes={"udp": lookup("udp", valid=False), "doh_fresh": lookup("doh_fresh", 13)}),
            dict(window=1, domain="x", rep=4, modes={"udp": lookup("udp", valid=False), "doh_fresh": lookup("doh_fresh", valid=False)}),
            dict(window=1, domain="x", rep=5, modes={"udp": lookup("udp", 10)}),
        ]
        effect, pairs = A.paired_statistics(blocks, "doh_fresh", "lookup", "failure-test")
        self.assertEqual(effect["blocks"], 5)
        for name in ("complete_pairs", "baseline_only_success", "comparison_only_success", "both_failed", "missing_comparison"):
            self.assertEqual(effect[name], 1, name)
        self.assertEqual(effect["median_delta_ms"], 3)
        self.assertEqual(len(pairs), 1)

    def test_no_successful_pairs_yields_no_effect_or_interval(self):
        block = dict(window=1, domain="x", rep=1, modes={"udp": lookup("udp", valid=False), "doh_fresh": lookup("doh_fresh", valid=False)})
        effect, _ = A.paired_statistics([block], "doh_fresh", "lookup", "empty-test")
        for key in ("median_delta_ms", "ci95_low_ms", "ci95_high_ms", "median_paired_pct_delta"):
            self.assertIsNone(effect[key])

    def test_zero_baseline_has_delta_but_no_percentage(self):
        block = dict(window=1, domain="x", rep=1, modes={"udp": lookup("udp", 0), "doh_fresh": lookup("doh_fresh", 3)})
        effect, _ = A.paired_statistics([block], "doh_fresh", "lookup", "zero-test")
        self.assertEqual(effect["median_delta_ms"], 3)
        self.assertIsNone(effect["median_paired_pct_delta"])

    def test_pairing_keeps_reused_domain_names_in_separate_windows(self):
        rows = [lookup("udp", 10, window=1), lookup("doh_fresh", 12, window=1),
                lookup("udp", 100, window=2), lookup("doh_fresh", 104, window=2)]
        groups = A.pairing(rows, "lookup")
        self.assertEqual(sorted(b["window"] for blocks in groups.values() for b in blocks), [1, 2])
        _, windows, _, _ = A.analyze_pairs(rows, "lookup")
        self.assertEqual([r["median_delta_ms"] for r in windows if r["comparison"] == "doh_fresh"], [2, 4])

    def test_duplicate_block_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            A.pairing([lookup("udp"), lookup("udp")], "lookup")

    def test_bootstrap_is_reproducible_and_empty_input_is_null(self):
        pairs = [dict(window=w, delta=v) for w, v in ((1, -5), (1, 1), (1, 6), (2, 2), (2, 9))]
        self.assertEqual(A.bootstrap(pairs, "fixed-label"), A.bootstrap(pairs, "fixed-label"))
        self.assertEqual(A.bootstrap([], "fixed-label"), (None, None))

    def test_marginals_count_failed_attempts_without_using_their_latency(self):
        result = A.marginal_summaries([lookup("udp", 10), lookup("udp", 20), lookup("udp", 3000, False)], "lookup")[0]
        self.assertEqual((result["attempted"], result["succeeded"], result["failed"]), (3, 2, 1))
        self.assertEqual(result["median_ms"], 15)

    def test_invalid_time_is_not_a_success(self):
        for bad in (-1, float("nan"), float("inf")):
            self.assertFalse(A.success(lookup("udp", bad), "lookup"))

    def test_failed_page_with_incomplete_gates_is_retained_as_failure(self):
        page = dict(id="timeout-page", provider="cloudflare", mode="udp", origins=8, window="w1", rep=0, status="error", error="Navigation timeout")
        audit = A.audit_pages([page], [])
        self.assertEqual(audit["validation_errors"], [])
        self.assertEqual(len(audit["unsuccessful_pages_with_diagnostics"]), 1)
        self.assertFalse(A.success(page, "page"))
        summary = A.marginal_summaries([page], "page")[0]
        self.assertEqual((summary["attempted"], summary["failed"], summary["succeeded"]), (1, 1, 0))
        self.assertIsNone(summary["median_ms"])

    def test_claimed_success_without_dns_gates_is_an_audit_error(self):
        page = dict(id="bad-success", provider="cloudflare", mode="udp", origins=1, window="w1", rep=0, status="ok", plt_ms=10, loaded_images=7, lookup_count=1)
        audit = A.audit_pages([page], [])
        self.assertEqual(len(audit["validation_errors"]), 1)
        self.assertFalse(A.success(page, "page"))

    def test_independent_wire_decoder_rejects_tampered_transaction(self):
        query = bytes.fromhex("123401000001000000000000076578616d706c6503636f6d0000010001")
        response = bytes.fromhex("123481800001000100000000") + query[12:] + bytes.fromhex("c00c000100010000012c00045db8d822")
        row = dict(query_base64=base64.b64encode(query).decode(), response_base64=base64.b64encode(response).decode(), valid=True)
        self.assertTrue(A.decode_wire(row, "example.com")["wire_valid"])
        row["response_base64"] = base64.b64encode(b"\x00\x00" + response[2:]).decode()
        with self.assertRaisesRegex(ValueError, "mismatch"):
            A.decode_wire(row, "example.com")

    def test_answer_owner_must_match_question_or_cname_target(self):
        query = bytes.fromhex("123401000001000000000000076578616d706c6503636f6d0000010001")
        question = bytes.fromhex("123481800001000100000000") + query[12:]
        foreign = b"\x05alias\x07example\x00"
        address = bytes.fromhex("000100010000012c00045db8d822")
        wrong_owner = question + foreign + address
        row = dict(query_base64=base64.b64encode(query), response_base64=base64.b64encode(wrong_owner))
        self.assertFalse(A.decode_wire(row, "example.com")["wire_valid"])
        with self.assertRaisesRegex(ValueError, "independent validity"):
            A.decode_wire({**row, "valid": True}, "example.com")
        header = question[:6] + b"\x00\x02" + question[8:]
        cname = b"\xc0\x0c" + bytes.fromhex("000500010000012c") + len(foreign).to_bytes(2, "big") + foreign
        linked = header + foreign + address + cname
        row["response_base64"] = base64.b64encode(linked)
        self.assertTrue(A.decode_wire(row, "example.com")["wire_valid"])


class CommandLineProperties(unittest.TestCase):
    def test_default_inputs_work_from_an_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory(prefix="dns-analysis-test-") as folder:
            output = Path(folder) / "results"
            result = subprocess.run([sys.executable, str(ROOT / "scripts/analyze.py"), "--out", str(output), "--expected-windows", "3", "--expected-reps", "10", "--strict"], cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["counts"]["lookup_measurements"], 1800)
            self.assertEqual(summary["counts"]["pages"], 360)
            self.assertEqual(summary["warnings"], [])
            self.assertEqual(summary["inputs"]["dns"], "data/dns_raw.jsonl")

    def test_one_window_dataset_has_no_hardcoded_three_window_warning(self):
        with tempfile.TemporaryDirectory(prefix="dns-small-design-test-") as folder:
            folder = Path(folder)
            raw = [json.loads(l) for l in (ROOT / "data/dns_raw.jsonl").read_text().splitlines() if l.strip()]
            pages = [json.loads(l) for l in (ROOT / "data/pages.jsonl").read_text().splitlines() if l.strip()]
            selected_dns = [r for r in raw if r.get("phase") == "measure" and r["window"] == 1 and r["rep"] == 1]
            selected_pages = [r for r in pages if A.win(r["window"]) == 1 and r["rep"] == 0]
            ids = {r["id"] for r in selected_pages}
            page_dns = [json.loads(l) for l in (ROOT / "data/page-dns.jsonl").read_text().splitlines() if l.strip()]
            selected_gates = [r for r in page_dns if r.get("page_id") in ids]
            for name, rows in (("dns_raw.jsonl", selected_dns), ("pages.jsonl", selected_pages), ("page-dns.jsonl", selected_gates)):
                (folder / name).write_text("".join(json.dumps(r) + "\n" for r in rows))
            cmd = [sys.executable, str(ROOT / "scripts/analyze.py"), "--dns", str(folder / "dns_raw.jsonl"), "--pages", str(folder / "pages.jsonl"), "--page-dns", str(folder / "page-dns.jsonl"), "--out", str(folder / "results"), "--expected-windows", "1", "--expected-reps", "1", "--strict"]
            result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((folder / "results/summary.json").read_text())
            self.assertEqual(summary["warnings"], [])
            self.assertEqual(summary["counts"]["lookup_measurements"], 60)
            self.assertEqual(summary["counts"]["pages"], 12)


if __name__ == "__main__":
    unittest.main()
