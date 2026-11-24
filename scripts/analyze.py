"""Analyze recorded DNS and controlled browser observations without network access.

Only raw measured JSONL inputs contribute to outputs. Artificial arrays in
self_checks() verify arithmetic in memory and are never exported as observations.
Requires Python 3.11+ with the pinned numpy dependency. Default paths are relative to the repository root.
"""
from __future__ import annotations

import argparse
import base64
import collections
import csv
import datetime as dt
import hashlib
import ipaddress
import json
import math
import re
import struct
from pathlib import Path

import numpy as np

SEED = 20261115
RESAMPLES = 4000
DNS_MODES = ("udp", "doh_fresh", "doh_warm")
PAGE_MODES = ("udp", "doh_fresh", "doh_reused")


def read_jsonl(path: Path, warnings: list[str]) -> list[dict]:
    if not path.exists():
        warnings.append(f"Input absent: {path}")
        return []
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    rows = []
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            # A concurrent collector may not have finished its last write.
            if i == len(lines) and not text.endswith("\n"):
                warnings.append(f"Ignored incomplete trailing line: {path}:{i}")
                continue
            raise ValueError(f"Malformed JSON at {path}:{i}")
        if not isinstance(value, dict):
            raise ValueError(f"Expected object at {path}:{i}")
        rows.append(value)
    return rows


def win(value) -> int:
    match = re.search(r"\d+", str(value))
    if match is None:
        raise ValueError(f"Bad window: {value!r}")
    return int(match.group())


def finite(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def describe(values) -> dict:
    a = np.asarray(list(values), dtype=float)
    if not len(a):
        return {k: None for k in ("median_ms", "q1_ms", "q3_ms", "iqr_ms", "p95_ms", "min_ms", "max_ms")}
    q1, med, q3 = np.quantile(a, [0.25, 0.5, 0.75], method="linear")
    ordered = np.sort(a)
    return {
        "median_ms": float(med), "q1_ms": float(q1), "q3_ms": float(q3),
        "iqr_ms": float(q3 - q1),
        "p95_ms": float(ordered[math.ceil(0.95 * len(a)) - 1]),
        "min_ms": float(ordered[0]), "max_ms": float(ordered[-1]),
    }


def stable_seed(label: str) -> int:
    return SEED ^ int.from_bytes(hashlib.sha256(label.encode()).digest()[:8], "big")


def bootstrap(pairs: list[dict], label: str) -> tuple[float | None, float | None]:
    """Resample paired blocks within each observed window, retaining window size.

    This conditions on the observed windows and successful pairs. It does not
    treat windows, repeated domain names, or the network as a population sample.
    """
    if not pairs:
        return None, None
    grouped = collections.defaultdict(list)
    for p in pairs:
        grouped[p["window"]].append(p["delta"])
    rng = np.random.default_rng(stable_seed(label))
    draws = []
    for window in sorted(grouped):
        a = np.asarray(grouped[window], dtype=float)
        indices = rng.integers(0, len(a), size=(RESAMPLES, len(a)))
        draws.append(a[indices])
    estimates = np.median(np.concatenate(draws, axis=1), axis=1)
    low, high = np.quantile(estimates, [0.025, 0.975], method="linear")
    return float(low), float(high)


def read_name(buf: bytes, start: int) -> tuple[str, int]:
    p, end, labels, seen = start, None, [], set()
    for _ in range(128):
        if p >= len(buf) or p in seen:
            raise ValueError("Truncated name or compression loop")
        seen.add(p)
        n = buf[p]
        if n & 0xC0 == 0xC0:
            if p + 1 >= len(buf):
                raise ValueError("Truncated pointer")
            if end is None:
                end = p + 2
            p = ((n & 0x3F) << 8) | buf[p + 1]
            continue
        if n & 0xC0:
            raise ValueError("Invalid label bits")
        p += 1
        if n == 0:
            return ".".join(labels).lower(), end if end is not None else p
        if p + n > len(buf):
            raise ValueError("Truncated label")
        labels.append(buf[p:p+n].decode("ascii"))
        p += n
    raise ValueError("Too many name hops")


def decode_wire(row: dict, expected_name: str | None = None) -> dict:
    """Independent Python decoder, not imported from collection implementation."""
    query = base64.b64decode(row["query_base64"], validate=True)
    response = base64.b64decode(row["response_base64"], validate=True)
    if len(query) < 12 or len(response) < 12:
        raise ValueError("DNS header shorter than 12 bytes")
    qi, qflags, qq, qa, qn, qx = struct.unpack_from("!6H", query)
    ri, flags, qd, an, ns, ar = struct.unpack_from("!6H", response)
    if qflags != 0x0100 or (qq, qa, qn, qx) != (1, 0, 0, 0):
        raise ValueError("Unexpected outgoing query flags/counts")
    qname, qp = read_name(query, 12)
    if qp + 4 != len(query) or struct.unpack_from("!HH", query, qp) != (1, 1):
        raise ValueError("Query is not one IN A question")
    rname, rp = read_name(response, 12)
    if ri != qi or not flags & 0x8000 or flags & 0x7800 or qd != 1:
        raise ValueError("Response ID/QR/opcode/question-count mismatch")
    if rp + 4 > len(response) or struct.unpack_from("!HH", response, rp) != (1, 1) or qname != rname:
        raise ValueError("Question mismatch")
    if expected_name and qname != expected_name.lower().rstrip("."):
        raise ValueError("Question differs from recorded hostname")
    p = rp + 4
    aliases, records = {}, []
    for sec, count in enumerate((an, ns, ar)):
        for _ in range(count):
            owner, p = read_name(response, p)
            if p + 10 > len(response):
                raise ValueError("Truncated RR header")
            typ, cls, ttl, size = struct.unpack_from("!HHIH", response, p)
            p += 10
            if p + size > len(response):
                raise ValueError("Truncated RR data")
            if sec == 0 and cls == 1 and typ == 5:
                target, consumed = read_name(response, p)
                if consumed != p + size or not target:
                    raise ValueError("Invalid CNAME RDATA")
                if owner in aliases and aliases[owner] != target:
                    raise ValueError("Conflicting CNAME records")
                aliases[owner] = target
            elif sec == 0 and cls == 1 and typ in (1, 28):
                if size != (4 if typ == 1 else 16):
                    raise ValueError("Bad address RDATA size")
                records.append((owner, str(ipaddress.ip_address(response[p:p+size])), ttl))
            p += size
    if p != len(response):
        raise ValueError("Unparsed trailing response bytes")
    reachable = set()
    current = qname
    while current is not None:
        if current in reachable:
            raise ValueError("CNAME chain loop")
        reachable.add(current)
        current = aliases.get(current)
    matching = [(address, ttl) for owner, address, ttl in records if owner in reachable]
    addresses = [address for address, _ in matching]
    ttls = [ttl for _, ttl in matching]
    rcode, tc = flags & 15, bool(flags & 0x0200)
    wire_valid = rcode == 0 and not tc and any(ipaddress.ip_address(a).version == 4 for a in addresses)
    for key, expected in (("rcode", rcode), ("truncated", tc), ("answer_count", an), ("response_bytes", len(response))):
        if key in row and row[key] != expected:
            raise ValueError(f"Reported {key} differs from independent decode")
    if "addresses" in row:
        reported = [str(ipaddress.ip_address(a)) for a in row["addresses"]]
        if sorted(reported) != sorted(addresses):
            raise ValueError("Reported addresses differ from independent decode")
    if "ttls" in row and sorted(row["ttls"]) != sorted(ttls):
        raise ValueError("Reported TTLs differ from independent decode")
    if row.get("valid") is True and not wire_valid:
        raise ValueError("Reported valid response fails independent validity check")
    return {"qname": qname, "rcode": rcode, "truncated": tc, "wire_valid": wire_valid}


def audit_dns(rows: list[dict], label: str, page_map: dict | None = None) -> dict:
    out = {
        "dataset": label, "rows": len(rows), "wire_responses": 0,
        "wire_decoded": 0, "wire_valid": 0, "without_response": 0,
        "validation_errors": [], "transport_mismatches": [],
        "doh_rows": 0, "h2_rows": 0, "tls_versions": {},
        "tls_resumed_true": 0, "tls_resumed_false": 0,
        "connection_preexisting_true": 0, "connection_preexisting_false": 0,
        "warm_measured_rows": 0, "warm_query_number_min": None,
        "warm_query_number_max": None,
    }
    tls = collections.Counter()
    warm_numbers = []
    for i, row in enumerate(rows, 1):
        name = row.get("domain") or row.get("hostname")
        page = (page_map or {}).get(row.get("page_id"), {})
        mode = row.get("protocol") or page.get("mode")
        prefix = f"row {i} {row.get('block_id') or row.get('page_id') or ''}"
        if row.get("response_base64"):
            out["wire_responses"] += 1
            try:
                decoded = decode_wire(row, name)
                out["wire_decoded"] += 1
                out["wire_valid"] += int(decoded["wire_valid"])
            except Exception as e:
                out["validation_errors"].append(f"{prefix}: {e}")
        else:
            out["without_response"] += 1
            if row.get("valid") is True:
                out["validation_errors"].append(f"{prefix}: valid row has no stored wire response")
        if mode and mode.startswith("doh"):
            out["doh_rows"] += 1
            out["h2_rows"] += int(row.get("alpn") == "h2")
            if row.get("tls_version"):
                tls[row["tls_version"]] += 1
            for val in (True, False):
                suffix = str(val).lower()
                if row.get("tls_session_reused") is val:
                    out[f"tls_resumed_{suffix}"] += 1
                if row.get("connection_preexisting") is val:
                    out[f"connection_preexisting_{suffix}"] += 1
            if row.get("valid") is True and (row.get("alpn") != "h2" or row.get("http_status") != 200):
                out["transport_mismatches"].append(f"{prefix}: DoH success without HTTP200/h2")
            if label == "lookup_measurements":
                if mode == "doh_fresh" and row.get("valid") is True:
                    if row.get("connection_preexisting") is not False or row.get("tls_session_reused") is not False or row.get("connection_query_number") != 1:
                        out["transport_mismatches"].append(f"{prefix}: fresh treatment mismatch")
                if mode == "doh_warm":
                    out["warm_measured_rows"] += 1
                    if finite(row.get("connection_query_number")):
                        warm_numbers.append(row["connection_query_number"])
                    if row.get("valid") is True and (row.get("connection_preexisting") is not True or row.get("connection_query_number", 0) <= 1):
                        out["transport_mismatches"].append(f"{prefix}: warm treatment mismatch")
            # Browser code explicitly opens the connection before querying, so
            # its query's preexisting flag does not distinguish fresh page gates.
    out["tls_versions"] = dict(tls)
    if warm_numbers:
        out["warm_query_number_min"] = min(warm_numbers)
        out["warm_query_number_max"] = max(warm_numbers)
    return out


def success(row: dict, experiment: str) -> bool:
    if experiment == "lookup":
        return row.get("valid") is True and finite(row.get("elapsed_ms"))
    return (row.get("status") == "ok" and row.get("_treatment_ok", True) and finite(row.get("plt_ms"))
            and row.get("loaded_images") == 7
            and row.get("lookup_count") == row.get("origins"))


def audit_pages(pages: list[dict], page_dns: list[dict]) -> dict:
    """Check per-page DNS gates and fresh/established treatment consistency.

    No socket UUID is stored, so matching connection properties plus continuous
    query numbering provide evidence consistent with reuse, not packet proof.
    """
    groups = collections.defaultdict(list)
    for row in page_dns:
        if row.get("phase") == "navigation":
            groups[row.get("page_id")].append(row)
    errors, unsuccessful_diagnostics, checked, doh_checked, udp_checked = [], [], 0, 0, 0
    expected_names = ["example.com", "example.net", "example.org", "iana.org", "wikipedia.org", "python.org", "kernel.org", "w3.org"]
    for page in pages:
        page_errors = []
        queries = groups.pop(page["id"], [])
        n = page["origins"]
        if len(queries) != n:
            page_errors.append(f"navigation query count {len(queries)}, expected {n}")
        hostnames = [r.get("hostname") for r in queries]
        if sorted(hostnames) != sorted(expected_names[:1] if n == 1 else expected_names):
            page_errors.append("navigation hostname set differs from fixture")
        mode = page["mode"]
        if mode.startswith("doh"):
            doh_checked += 1
            numbers = [r.get("connection_query_number") for r in queries]
            start = 1 if mode == "doh_fresh" else 2
            if sorted(numbers, key=lambda x: -1 if x is None else x) != list(range(start, start+n)):
                page_errors.append(f"query numbers {numbers}, expected consecutive {start}..{start+n-1}")
            if any(r.get("connection_preexisting") is not True for r in queries):
                page_errors.append("explicitly opened DoH query lacks preexisting connection")
            if any(r.get("alpn") != "h2" for r in queries):
                page_errors.append("navigation DoH query lacks h2")
            if any(r.get("tls_session_reused") is not False for r in queries):
                page_errors.append("TLS resumption is true or unrecorded")
            connection_times = [r.get("connect_ms") for r in queries]
            if not connection_times or any(not finite(t) for t in connection_times):
                page_errors.append("missing connection setup time")
            elif max(connection_times)-min(connection_times) > 1e-9:
                page_errors.append("connection setup property changed within page")
            expected_ip = {"cloudflare": "1.1.1.1", "google": "8.8.8.8"}.get(page["provider"])
            if any(r.get("remote_address") != expected_ip for r in queries):
                page_errors.append("unexpected or missing resolver remote IP")
            if len({r.get("tls_version") for r in queries}) > 1:
                page_errors.append("TLS version changed within page")
        else:
            udp_checked += 1
        if any(r.get("valid") is not True for r in queries):
            page_errors.append("invalid DNS query among navigation gates")
        page["_treatment_ok"] = not page_errors
        if page_errors:
            page["_analysis_error"] = "; ".join(page_errors)
            diagnostic = {"page_id": page["id"], "recorded_status": page.get("status"), "errors": page_errors}
            if page.get("status") == "ok":
                errors.append(diagnostic)
            else:
                # A recorded network/page failure may legitimately stop before
                # every DNS gate completes. Retain its diagnostics and count it
                # as an unsuccessful attempt, rather than a false success or a
                # corrupted successful treatment.
                unsuccessful_diagnostics.append(diagnostic)
        checked += 1
    return {
        "dataset": "page_treatment_audit", "pages_checked": checked,
        "doh_pages_checked": doh_checked, "udp_pages_checked": udp_checked,
        "pages_with_treatment_errors": len(errors), "validation_errors": errors,
        "unsuccessful_pages_with_diagnostics": unsuccessful_diagnostics,
        "transport_mismatches": [],
        "navigation_rows_without_completed_page": sum(len(v) for v in groups.values()),
        "interpretation": "DoH query preexisting=true is expected in both page modes because the collector explicitly opens the connection before querying. Continuous numbering (fresh 1..N, established 2..N+1), identical stored connect_ms, h2 and no TLS resumption were checked per page. No socket UUID was recorded.",
    }


def value(row: dict, experiment: str) -> float:
    return float(row["elapsed_ms" if experiment == "lookup" else "plt_ms"])


def marginal_summaries(rows: list[dict], experiment: str) -> list[dict]:
    groups = collections.defaultdict(list)
    for row in rows:
        key = (row["provider"], row.get("origins", ""), row["protocol"] if experiment == "lookup" else row["mode"])
        groups[key].append(row)
    results = []
    for (provider, origins, mode), group in sorted(groups.items()):
        ok = [r for r in group if success(r, experiment)]
        result = {
            "provider": provider, "origins": origins, "mode": mode,
            "attempted": len(group), "succeeded": len(ok), "failed": len(group)-len(ok),
            "windows": ";".join(map(str, sorted({win(r["window"]) for r in group}))),
            **describe(value(r, experiment) for r in ok),
        }
        errors = collections.Counter(str(r.get("_analysis_error") or r.get("error") or r.get("errors") or r.get("status") or "invalid response") for r in group if not success(r, experiment))
        result["failure_reasons"] = json.dumps(dict(errors), ensure_ascii=False, sort_keys=True)
        results.append(result)
    return results


def pairing(rows: list[dict], experiment: str):
    blocks = collections.defaultdict(dict)
    for row in rows:
        group = (row["provider"], row.get("origins", ""))
        key = (group, win(row["window"]), row.get("domain", ""), row["rep"])
        mode = row["protocol"] if experiment == "lookup" else row["mode"]
        if mode in blocks[key]:
            raise ValueError(f"Duplicate measurement block/mode: {experiment} {key} {mode}")
        blocks[key][mode] = row
    grouped = collections.defaultdict(list)
    for (group, window, domain, rep), modes in blocks.items():
        grouped[group].append({"window": window, "domain": domain, "rep": rep, "modes": modes})
    return grouped


def paired_statistics(blocks: list[dict], comparison: str, experiment: str, label: str, with_ci=True):
    counts = collections.Counter()
    pairs = []
    for block in blocks:
        modes = block["modes"]
        base, other = modes.get("udp"), modes.get(comparison)
        counts["blocks"] += 1
        if base is None:
            counts["missing_baseline"] += 1
        if other is None:
            counts["missing_comparison"] += 1
        if base is None or other is None:
            continue
        counts["both_attempted"] += 1
        bs, cs = success(base, experiment), success(other, experiment)
        if bs and cs:
            b, c = value(base, experiment), value(other, experiment)
            pairs.append({"window": block["window"], "domain": block["domain"], "rep": block["rep"], "delta": c-b, "pct_delta": 100*(c-b)/b if b > 0 else None})
        elif bs:
            counts["baseline_only_success"] += 1
        elif cs:
            counts["comparison_only_success"] += 1
        else:
            counts["both_failed"] += 1
    low, high = bootstrap(pairs, label) if with_ci else (None, None)
    deltas = [p["delta"] for p in pairs]
    percentages = [p["pct_delta"] for p in pairs if p["pct_delta"] is not None]
    result = {k: counts[k] for k in ("blocks", "both_attempted", "missing_baseline", "missing_comparison", "baseline_only_success", "comparison_only_success", "both_failed")}
    result.update({
        "complete_pairs": len(pairs), "median_delta_ms": float(np.median(deltas)) if deltas else None,
        "ci95_low_ms": low, "ci95_high_ms": high,
        "median_paired_pct_delta": float(np.median(percentages)) if percentages else None,
    })
    return result, pairs


def analyze_pairs(rows: list[dict], experiment: str):
    overall, by_window, leaveout, domains = [], [], [], []
    comparisons = ("doh_fresh", "doh_warm" if experiment == "lookup" else "doh_reused")
    for (provider, origins), blocks in sorted(pairing(rows, experiment).items()):
        for comparison in comparisons:
            prefix = {"experiment": experiment, "provider": provider, "origins": origins, "comparison": comparison, "baseline": "udp"}
            label = f"{experiment}/{provider}/{origins}/{comparison}"
            stats, _ = paired_statistics(blocks, comparison, experiment, label)
            overall.append({**prefix, **stats})
            windows = sorted({b["window"] for b in blocks})
            for w in windows:
                subset = [b for b in blocks if b["window"] == w]
                stats, _ = paired_statistics(subset, comparison, experiment, label + f"/window{w}", with_ci=False)
                by_window.append({**prefix, "window": w, **stats})
                subset = [b for b in blocks if b["window"] != w]
                stats, _ = paired_statistics(subset, comparison, experiment, label + f"/omit{w}", with_ci=False)
                leaveout.append({**prefix, "omitted_window": w, **stats})
            if experiment == "lookup":
                for name in sorted({b["domain"] for b in blocks}):
                    subset = [b for b in blocks if b["domain"] == name]
                    stats, _ = paired_statistics(subset, comparison, experiment, label + f"/domain{name}", with_ci=False)
                    domains.append({**prefix, "domain": name, **stats})
    return overall, by_window, leaveout, domains


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def self_checks():
    d = describe([1, 2, 3, 4])
    assert d["median_ms"] == 2.5 and d["iqr_ms"] == 1.5 and d["p95_ms"] == 4
    assert describe([])["median_ms"] is None
    pairs = [{"window": w, "delta": 3.0} for w in (1, 1, 2, 2)]
    assert bootstrap(pairs, "selfcheck") == (3.0, 3.0)
    assert bootstrap([], "selfcheck") == (None, None)
    # Pairwise subtraction must happen before aggregation.
    b = np.array([1., 10., 100.])
    c = np.array([2., 12., 104.])
    assert float(np.median(c-b)) == 2.0
    return "Passed in-memory arithmetic and deterministic bootstrap checks"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent.parent
    parser.add_argument("--dns", type=Path, default=root / "data/dns_raw.jsonl")
    parser.add_argument("--pages", type=Path, default=root / "data/pages.jsonl")
    parser.add_argument("--page-dns", type=Path, default=root / "data/page-dns.jsonl")
    parser.add_argument("--out", type=Path, default=root / "results")
    parser.add_argument("--expected-windows", type=int, help="Optional completed-design window count; omitted means no fixed-count warning")
    parser.add_argument("--expected-reps", type=int, help="Optional repetitions per window/domain/layout")
    parser.add_argument("--strict", action="store_true", help="Exit unsuccessfully if audits or requested design checks fail")
    args = parser.parse_args()
    if (args.expected_windows is None) != (args.expected_reps is None):
        parser.error("Use --expected-windows and --expected-reps together")
    if args.expected_windows is not None and (args.expected_windows < 1 or args.expected_reps < 1):
        parser.error("Expected windows and repetitions must be positive")
    checks = self_checks()
    warnings = []
    raw_dns = read_jsonl(args.dns, warnings)
    lookup_rows = [r for r in raw_dns if r.get("phase") == "measure"]
    page_rows = read_jsonl(args.pages, warnings)
    page_dns = read_jsonl(args.page_dns, warnings)
    page_map = {p["id"]: p for p in page_rows}
    if len(page_map) != len(page_rows):
        raise ValueError("Duplicate page IDs")
    page_treatment_audit = audit_pages(page_rows, page_dns)
    dns_summary = marginal_summaries(lookup_rows, "lookup")
    page_summary = marginal_summaries(page_rows, "page")
    dns_paired, dns_windows, dns_leave, domain_effects = analyze_pairs(lookup_rows, "lookup")
    page_paired, page_windows, page_leave, _ = analyze_pairs(page_rows, "page")
    audits = [audit_dns(lookup_rows, "lookup_measurements"), audit_dns([r for r in raw_dns if r.get("phase") != "measure"], "lookup_priming"), audit_dns([r for r in page_dns if r.get("phase") == "navigation"], "page_navigation_queries", page_map), audit_dns([r for r in page_dns if r.get("phase") not in ("navigation", "gate-error")], "page_priming", page_map), page_treatment_audit]
    window_times = []
    for experiment, rows, field in (("lookup", lookup_rows, "started_utc"), ("page", page_rows, "utc")):
        for w in sorted({win(r["window"]) for r in rows}):
            subset = [r for r in rows if win(r["window"]) == w]
            starts = [r[field] for r in subset if r.get(field)]
            window_times.append({"experiment": experiment, "window": w, "attempts": len(subset), "first_start_utc": min(starts) if starts else None, "last_start_utc": max(starts) if starts else None})
    if args.expected_windows is not None:
        expected_window_ids = set(range(1, args.expected_windows + 1))
        for experiment, rows in (("Lookup", lookup_rows), ("Page", page_rows)):
            actual_window_ids = {win(r["window"]) for r in rows}
            if actual_window_ids != expected_window_ids:
                warnings.append(f"{experiment} windows {sorted(actual_window_ids)}, expected {sorted(expected_window_ids)}")
        domains = {r["domain"] for r in lookup_rows}
        expected_lookups = args.expected_windows * args.expected_reps * len(domains)
        for r in dns_summary:
            if r["attempted"] != expected_lookups:
                warnings.append(f"Lookup {r['provider']}/{r['mode']}: {r['attempted']} attempts, expected {expected_lookups}")
        expected_pages = args.expected_windows * args.expected_reps
        for r in page_summary:
            if r["attempted"] != expected_pages:
                warnings.append(f"Page {r['provider']}/{r['origins']}/{r['mode']}: {r['attempted']} attempts, expected {expected_pages}")
    def input_label(p):
        try:
            return Path(p).resolve().relative_to(root).as_posix()
        except ValueError:
            return str(Path(p).resolve())
    summary = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": {"dns": input_label(args.dns), "pages": input_label(args.pages), "page_dns": input_label(args.page_dns)},
        "expected_design": {"windows": args.expected_windows, "reps": args.expected_reps},
        "seed": SEED, "resamples": RESAMPLES, "numpy_version": np.__version__,
        "statistics": {
            "marginals": "Successful observations only. Median and IQR use linear quantile interpolation; p95 uses nearest rank ceil(0.95*n). Failures retained as counts.",
            "paired_effect": "Median of within-block DoH minus UDP differences; percentage is median of paired percentage differences, not ratio of marginal medians.",
            "interval": "Exploratory percentile 95% interval from 4000 bootstrap resamples of complete paired blocks within each observed window. Window counts remain fixed. Conditional on these sampled windows, names, network and successful pairs. Repeated domains and serial dependence may narrow intervals; no population coverage claim.",
            "unit_lookup": "Provider, domain, window, repetition matched block. Protocol responses are paired before resampling.",
            "unit_page": "Provider, layout, window, repetition matched navigation block. Nested resource queries are not independent pages.",
            "robustness": "Per-window paired medians, leave-one-window-out medians, and per-domain lookup effects. Three windows are insufficient for robust between-window inference. Page p95 with 30 observations is descriptive.",
            "missingness": "No imputation. Successful paired effect conditions on both modes succeeding; discordant successes and missing records are reported.",
        },
        "counts": {"lookup_all_rows": len(raw_dns), "lookup_measurements": len(lookup_rows), "pages": len(page_rows), "page_dns_rows": len(page_dns), "lookup_phase_counts": dict(collections.Counter(r.get("phase") for r in raw_dns)), "page_dns_phase_counts": dict(collections.Counter(r.get("phase") for r in page_dns))},
        "lookup_summary": dns_summary, "lookup_paired": dns_paired,
        "page_summary": page_summary, "page_paired": page_paired,
        "window_times": window_times,
        "window_effects": dns_windows + page_windows,
        "loo": dns_leave + page_leave,
        "domain_effects": domain_effects,
        "validation": {a["dataset"]: a for a in audits},
        "self_checks": checks, "warnings": warnings,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    for name, rows in (("lookup_summary.csv", dns_summary), ("lookup_paired.csv", dns_paired), ("page_summary.csv", page_summary), ("page_paired.csv", page_paired), ("window_effects.csv", dns_windows+page_windows), ("leave_one_window_out.csv", dns_leave+page_leave), ("domain_effects.csv", domain_effects), ("window_times.csv", window_times)):
        write_csv(args.out / name, rows)
    report = {"counts": summary["counts"], "validation_errors": sum(len(a["validation_errors"]) for a in audits), "transport_mismatches": sum(len(a["transport_mismatches"]) for a in audits), "warnings": warnings}
    print(json.dumps(report, indent=2))
    if args.strict and (report["validation_errors"] or report["transport_mismatches"] or warnings):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
