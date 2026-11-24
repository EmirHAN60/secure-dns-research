"""Check the independently generated schedules in the saved 22–23 November sessions."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from robustness import read_jsonl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    root = parser.parse_args().root
    plan = json.loads((root / "docs/SESSION_EXTENSION_PLAN.json").read_text(encoding="utf-8"))
    final = json.loads((root / "docs/ADDITIONAL_DATE_PLAN.json").read_text(encoding="utf-8"))["session"]
    group_by_schedule = defaultdict(list)
    all_windows = 0
    for session in [*plan["sessions"], final]:
        raw = root / session["directory"] / "control_raw.jsonl"
        windows = defaultdict(list)
        for row in read_jsonl(raw):
            if row["phase"] == "measure":
                windows[row["window"]].append(
                    tuple(row[key] for key in ("provider", "domain", "rep", "protocol", "order"))
                )
        if len(windows) != session["windows"]:
            raise ValueError(f"Missing historical windows in {session['session_id']}")
        all_windows += len(windows)
        for window, records in sorted(windows.items()):
            canonical = json.dumps(records, separators=(",", ":"), ensure_ascii=True).encode("ascii")
            fingerprint = hashlib.sha256(canonical).hexdigest()
            group_by_schedule[fingerprint].append({"session_id": session["session_id"], "window": window})
    result = {
        "measured_windows": all_windows,
        "distinct_orders": len(group_by_schedule),
        "groups_by_schedule_sha256": dict(group_by_schedule),
        "scope": "Ordered measured provider, domain, repetition, protocol and slot tuples. Historical captures.",
    }
    payload = json.dumps(result, indent=2) + "\n"
    (root / "results/historical_order_audit.json").write_text(payload, encoding="utf-8")
    print(f"Historical order audit: {len(group_by_schedule)} distinct schedules in {all_windows} windows")


if __name__ == "__main__":
    main()
