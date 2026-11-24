"""Validate the additional-date run and score the unchanged calibration forecast."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from control_analysis import control_pairs, sign
from session_analysis import audit_session, category, fingerprint, metric_stats, sha, threshold_rates, utc
from robustness import read_jsonl, window_id


def analyze(root):
    extension = root / "docs/SESSION_EXTENSION_PLAN.json"
    plan = json.loads(extension.read_text(encoding="utf-8"))
    verification = json.loads((root / "docs/ADDITIONAL_DATE_PLAN.json").read_text(encoding="utf-8"))
    if sha(extension) != verification["original_plan_sha256"]:
        raise ValueError("The original forecast plan differs from the plan referenced before verification")
    planned = verification["session"]
    folder = root / planned["directory"]
    env = json.loads((folder / "environment.json").read_text(encoding="utf-8"))
    if env["status"] != "complete" or utc(env["started_utc"]) <= utc(verification["recorded_utc"]):
        raise ValueError("Additional-date collection is incomplete or preceded its plan")
    calibration = json.loads((root / "data/control-2026-11-20/environment.json").read_text(encoding="utf-8"))
    if any(env[key] != calibration[key] for key in ("release", "node", "openssl", "arch")):
        raise ValueError("Additional-date runtime differs from the forecast calibration")
    rows = read_jsonl(folder / "control_raw.jsonl")
    audit = audit_session(root, planned, plan, env, rows)
    if audit["errors"]:
        raise ValueError(f"Additional-date wire or design audit failed: {audit['errors']}")
    effects = []
    for forecast in plan["calibration"]["forecasts_for_each_new_session"]:
        provider, comparison, baseline, metric = (
            forecast[k] for k in ("provider", "comparison", "baseline", "metric")
        )
        blocks = defaultdict(dict)
        for row in rows:
            if row["phase"] == "measure" and row["provider"] == provider:
                block = (window_id(row["window"]), row["domain"], row["rep"])
                blocks[block][row["protocol"]] = row
        pairs, counts = control_pairs(blocks, comparison, baseline, metric, env["started_utc"][:10])
        stats = metric_stats(pair["delta_ms"] for pair in pairs)
        actual, predicted = stats["median_delta_ms"], forecast["calibration_point_ms"]
        rates = threshold_rates(pairs, {}, plan["thresholds_ms"])
        categories = {row["threshold_ms"]: row["category"] for row in forecast["threshold_categories"]}
        for rate in rates:
            threshold = rate["threshold_ms"]
            observed = category(actual, threshold)
            rate.update(observed_category=observed, predicted_category=categories[threshold],
                        category_matches=observed == categories[threshold])
        effects.append({
            "provider": provider, "baseline": baseline, "metric": metric, **stats, "pair_audit": counts,
            "forecast_point_ms": predicted, "sign_matches": sign(predicted) == sign(actual),
            "forecast_absolute_error_ms": abs(actual - predicted), "zero_absolute_error_ms": abs(actual),
            "window_paired_medians_ms": [
                metric_stats(p["delta_ms"] for p in pairs if p["window"] == w)["median_delta_ms"]
                for w in range(1, planned["windows"] + 1)
            ],
            "thresholds": rates,
        })
    return {
        "data_directory": planned["directory"], "started_utc": env["started_utc"], "finished_utc": env["finished_utc"],
        "plan_recorded_utc": verification["recorded_utc"], "build_group": fingerprint(env)[0], "audit": audit,
        "scope": "Additional date held out from the original 20 November forecast. One session on the same host.",
        "comparisons": effects,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    root = parser.parse_args().root
    result = analyze(root)
    payload = json.dumps(result, indent=2) + "\n"
    (root / "results/additional_date.json").write_text(payload, encoding="utf-8")
    print(f"Audited additional-date collection: {result['audit']['measured_attempts']} attempts, "
          f"{result['audit']['failed_measured_attempts']} failed")


if __name__ == "__main__":
    main()
