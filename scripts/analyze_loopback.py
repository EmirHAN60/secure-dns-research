"""Validate saved loopback DNS replies and summarize paired lifecycle timings."""

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

from analyze import decode_wire


def analyze(root, folder):
    meta = json.loads((folder / "loopback_environment.json").read_text(encoding="utf-8"))
    records = [json.loads(line) for line in (folder / "loopback_raw.jsonl").read_text(encoding="utf-8").splitlines()]
    if meta["status"] != "complete" or len(records) != 2 * (meta["warmups"] + meta["repetitions"]):
        raise ValueError("Incomplete loopback dataset")
    source_candidates = {
        "script_sha256": [root / "scripts/measure_loopback.mjs"],
        "client_sha256": [
            root / "scripts/dns_client.mjs",
            root / "docs/evidence/collection-source-2026-11-22/dns_client.mjs",
        ],
    }
    for key, candidates in source_candidates.items():
        if not any(hashlib.sha256(source.read_bytes()).hexdigest() == meta[key] for source in candidates):
            raise ValueError(f"No loopback source matches its recorded checksum: {key}")
    blocks = defaultdict(dict)
    ports = set()
    queries = set()
    for row in records:
        rep, treatment = row["rep"], row["treatment"]
        if treatment in blocks[rep] or treatment not in {"fresh", "prebound"}:
            raise ValueError("Invalid or duplicate loopback treatment")
        if row["query_base64"] in queries:
            raise ValueError("Duplicate loopback transaction")
        queries.add(row["query_base64"])
        if row["phase"] != ("warmup" if rep < meta["warmups"] else "measure"):
            raise ValueError("Unexpected loopback phase")
        if row["valid"]:
            parsed = decode_wire({**row, "addresses": [meta["answer"]]}, meta["name"])
            if not parsed["wire_valid"]:
                raise ValueError(f"Loopback DNS wire audit failed: {parsed}")
            values = [row[field] for field in ("ready_ms", "query_ms", "whole_ms")]
            if not all(math.isfinite(value) and value >= 0 for value in values):
                raise ValueError("Invalid loopback timing")
            if values[2] + 1e-6 < values[0] + values[1]:
                raise ValueError("Loopback stages exceed whole call")
            if treatment == "prebound":
                ports.add(row["port"])
        blocks[rep][treatment] = row
    if set(blocks) != set(range(meta["warmups"] + meta["repetitions"])) or len(ports) != 1:
        raise ValueError("Unexpected loopback block grid or reusable source port")
    for block in blocks.values():
        if set(block) != {"fresh", "prebound"} or {row["order"] for row in block.values()} != {1, 2}:
            raise ValueError("Incomplete loopback pair")
    failures = sum(not row["valid"] for row in records)
    if failures != meta["failed"]:
        raise ValueError("Loopback failure counts disagree")
    pairs = [
        block for rep, block in blocks.items()
        if rep >= meta["warmups"] and all(row["valid"] for row in block.values())
    ]
    if not pairs:
        raise ValueError("No complete loopback pairs")
    return {
        "attempts": 2 * meta["repetitions"], "complete_pairs": len(pairs), "failures_including_warmups": failures,
        "fresh_ready_median_ms": median(block["fresh"]["ready_ms"] for block in pairs),
        "whole_paired_median_ms": median(block["fresh"]["whole_ms"] - block["prebound"]["whole_ms"]
                                       for block in pairs),
        "query_paired_median_ms": median(block["fresh"]["query_ms"] - block["prebound"]["query_ms"]
                                       for block in pairs),
        "scope": "Single host and process, deterministic DNS responder on IPv4 loopback; no public resolver.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--data", type=Path, help="Loopback input directory. Defaults to the published collection.")
    parser.add_argument("--out", type=Path, help="Result JSON destination. Defaults to the published summary.")
    args = parser.parse_args()
    if args.data is not None and args.out is None:
        parser.error("Choose --out when analyzing a different --data directory")
    root = args.root
    summary = analyze(root, args.data or root / "data/loopback-2026-11-22")
    payload = json.dumps(summary, indent=2) + "\n"
    (args.out or root / "results/loopback_summary.json").write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
