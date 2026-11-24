"""Analyze historical window stability and the separately defined UDP control.

All uncertainty intervals here are conditional resampling summaries for fixed
observed windows. No selected window is treated as an independent population
sample, and the new explicit-bind estimator is kept distinct from history.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from analyze import decode_wire
from robustness import datasets, paired_rows, read_jsonl, window_id

SEED = 20261120
RESAMPLES = 4000
PROVIDERS = ("cloudflare", "google")


def med(values):
    values = list(values)
    return float(np.median(values)) if values else None


def sign(value):
    return 1 if value > 0 else -1 if value < 0 else 0


def stable_rng(label):
    return np.random.default_rng(SEED ^ int.from_bytes(hashlib.sha256(label.encode()).digest()[:8], "big"))


def conditional_interval(pairs, label):
    """Resample pairs inside each fixed window, preserving its observed size."""
    grouped = defaultdict(list)
    for pair in pairs:
        grouped[pair["window_key"]].append(pair["delta_ms"])
    if not grouped:
        return [None, None]
    rng = stable_rng(label)
    samples = []
    for key in sorted(grouped):
        a = np.asarray(grouped[key], dtype=float)
        samples.append(a[rng.integers(0, len(a), size=(RESAMPLES, len(a)))])
    estimates = np.median(np.concatenate(samples, axis=1), axis=1)
    return [float(x) for x in np.quantile(estimates, [.025, .975])]


def describe(values):
    a = np.asarray(list(values), dtype=float)
    if not len(a):
        return {"n": 0, "median_ms": None, "q1_ms": None, "q3_ms": None, "min_ms": None, "max_ms": None}
    q1, median, q3 = np.quantile(a, [.25,.5,.75])
    return {"n":len(a), "median_ms":float(median), "q1_ms":float(q1), "q3_ms":float(q3),
            "min_ms":float(a.min()), "max_ms":float(a.max())}


def window_summaries(pairs, meta):
    groups = defaultdict(list)
    for pair in pairs:
        groups[pair["window_key"]].append(pair)
    out = []
    for key, selected in sorted(groups.items(),key=lambda item:(item[1][0]["date"],item[1][0]["window"])):
        delta = [p["delta_ms"] for p in selected]
        info = selected[0]
        out.append({**meta, "window_key":key, "date":info["date"], "window":info["window"],
                    **describe(delta), "median_paired_pct_delta":med(p["delta_pct"] for p in selected),
                    "median_sign":sign(med(delta)),
                    "positive_pairs":sum(x>0 for x in delta), "negative_pairs":sum(x<0 for x in delta),
                    "zero_pairs":sum(x==0 for x in delta)})
    return out


def aggregate(pairs, windows, meta, interval=True):
    delta = [p["delta_ms"] for p in pairs]
    ws = [w["median_ms"] for w in windows]
    return {**meta, "complete_pairs":len(pairs), "observed_windows":len(windows),
            "pooled_median_ms":med(delta),
            "conditional_fixed_window_interval_ms":conditional_interval(pairs, str(meta)) if interval else [None,None],
            "median_paired_pct_delta":med(p["delta_pct"] for p in pairs),
            "median_of_window_medians_ms":med(ws),
            "mean_of_window_medians_ms":float(np.mean(ws)) if ws else None,
            "window_median_min_ms":min(ws) if ws else None,
            "window_median_max_ms":max(ws) if ws else None,
            "positive_window_count":sum(x>0 for x in ws), "negative_window_count":sum(x<0 for x in ws),
            "zero_window_count":sum(x==0 for x in ws),
            "positive_pair_count":sum(x>0 for x in delta), "negative_pair_count":sum(x<0 for x in delta),
            "zero_pair_count":sum(x==0 for x in delta)}


def historical_analysis(root):
    history = [d for d in datasets(root) if d["date"] in ("2026-11-15", "2026-11-19")]
    if len(history) != 2:
        raise ValueError("Historical analysis requires the separate 15 and 19 November summaries")
    contrasts, windows, held, date_checks = [], [], [], []
    for provider in PROVIDERS:
        for mode in ("doh_fresh", "doh_warm"):
            meta = {"provider":provider, "comparison":mode, "baseline":"udp", "metric":"elapsed_ms"}
            pairs = []
            for ds in history:
                pairs.extend({**p, "date":ds["date"], "window_key":f"{ds['date']}:w{p['window']}"}
                             for p in paired_rows(ds, "lookup", provider, mode))
            current_windows = window_summaries(pairs, meta)
            windows.extend(current_windows)
            pooled = aggregate(pairs, current_windows, meta)
            for w in current_windows:
                training = [p for p in pairs if p["window_key"] != w["window_key"]]
                prediction = med(p["delta_ms"] for p in training)
                held.append({**meta, "held_window":w["window_key"], "training_pairs":len(training),
                             "held_pairs":w["n"], "training_pooled_median_ms":prediction,
                             "predicted_sign":sign(prediction), "held_median_ms":w["median_ms"],
                             "observed_sign":w["median_sign"], "sign_agrees":sign(prediction)==w["median_sign"],
                             "absolute_prediction_error_ms":abs(prediction-w["median_ms"])})
            own = [h for h in held if all(h[k] == meta[k] for k in meta)]
            pooled["retrospective_leave_window_sign_agrees"] = sum(h["sign_agrees"] for h in own)
            pooled["retrospective_leave_window_checks"] = len(own)
            pooled["retrospective_leave_window_mae_ms"] = float(np.mean([h["absolute_prediction_error_ms"] for h in own]))
            pooled["retrospective_zero_adjustment_mae_ms"] = float(np.mean([abs(h["held_median_ms"]) for h in own]))
            pooled["retrospective_mae_improvement_over_zero_ms"] = pooled["retrospective_zero_adjustment_mae_ms"] - pooled["retrospective_leave_window_mae_ms"]
            contrasts.append(pooled)
            for date in sorted(set(p["date"] for p in pairs)):
                training = [p for p in pairs if p["date"] != date]
                test = [p for p in pairs if p["date"] == date]
                pred, observed = med(p["delta_ms"] for p in training), med(p["delta_ms"] for p in test)
                test_windows = [w for w in current_windows if w["date"] == date]
                date_checks.append({**meta, "held_date":date, "training_pairs":len(training),
                                    "held_pairs":len(test), "training_pooled_median_ms":pred,
                                    "held_date_pooled_median_ms":observed,
                                    "date_sign_agrees":sign(pred)==sign(observed),
                                    "held_window_sign_agrees":sum(sign(pred)==w["median_sign"] for w in test_windows),
                                    "held_window_count":len(test_windows),
                                    "absolute_prediction_error_ms":abs(pred-observed)})
    return {"dates":[d["date"] for d in history], "pooled_contrasts":contrasts, "windows":windows,
            "held_window_checks":held, "date_holdouts":date_checks,
            "scope":"The pooled historical statistic describes exactly these six fixed windows. Its conditional resampling interval resamples within each window while retaining every window. It is not a population confidence interval. Retrospective held-window and held-date checks reuse selected historical data; they are not a prospective prediction experiment. The median of window medians gives one weight to each observed window, a different statistic from the pooled pair median."}


def row_mode(row):
    return row.get("protocol", row.get("mode"))


def control_metric(row, metric):
    if metric in row:
        return float(row[metric])
    if metric == "post_bind_query_ms" and "post_bind_elapsed_ms" in row:
        return float(row["post_bind_elapsed_ms"])
    return None


def verify_frozen_history(root):
    plan=json.loads((root/"docs/control_analysis_plan.json").read_text(encoding="utf-8"))
    verified={}
    for relative,expected in plan["input_sha256"].items():
        actual=hashlib.sha256((root/relative).read_bytes()).hexdigest()
        if actual!=expected:
            raise ValueError(f"Historical input differs from frozen forecast: {relative}")
        verified[relative]=actual
    return verified


def control_audit(root,records,env,plan,directory):
    """Strict design and treatment checks; run only after collection completes."""
    errors=[]
    measured=[r for r in records if r.get("phase")=="measure"]
    primers=[r for r in records if r.get("phase")=="prime"]
    expected_modes={"udp_fresh","udp_bound","doh_warm"}
    providers=set(env["providers"])
    domains=set(env["domains"])
    expected_windows=set(range(1,int(env["windows"])+1))
    expected_reps=set(range(1,int(env["reps"])+1))
    expected_n=len(providers)*len(domains)*len(expected_windows)*len(expected_reps)*3
    if len(measured)!=expected_n or expected_n!=env["expected_measured_attempts"]:
        errors.append(f"Measurement count {len(measured)} differs from expected {expected_n}")
    if len(primers)!=len(providers)*len(domains)*len(expected_windows)*3:
        errors.append("Priming grid count mismatch")
    if len(records)!=len(measured)+len(primers):errors.append("Unexpected record phase")
    grid=defaultdict(dict)
    prime_grid=set()
    for row in records:
        provider,domain,mode=row.get("provider"),row.get("domain"),row_mode(row)
        window=window_id(row["window"])
        if provider not in providers or domain not in domains or mode not in expected_modes or window not in expected_windows:
            errors.append("Record outside declared provider/domain/mode/window grid")
            continue
        if row.get("phase")=="measure":
            if row.get("rep") not in expected_reps:errors.append("Repetition outside declared grid")
            key=(provider,window,domain,row.get("rep"))
            if mode in grid[key]:errors.append(f"Duplicate measured treatment {key} {mode}")
            grid[key][mode]=row
        else:
            key=(provider,window,domain,mode)
            if key in prime_grid:errors.append("Duplicate primer")
            prime_grid.add(key)
        for key,value in row.items():
            if key.endswith("_ms") and value is not None:
                if not isinstance(value,(int,float)) or not np.isfinite(value) or value<0:
                    errors.append(f"Invalid nonnegative timing stage {key}")
        if row.get("valid") is not True:continue
        ip=env["providers"][provider]["ip"]
        if row.get("remote_address")!=ip:errors.append("Requested provider IP mismatch")
        port=row.get("local_port")
        if not isinstance(port,int) or not 0<port<=65535:errors.append("Invalid local port")
        if mode.startswith("udp_"):
            if row.get("remote_port")!=53 or row.get("udp_connected") is not False:
                errors.append("UDP endpoint or unconnected-socket flag mismatch")
            if row.get("bound_before_timing") is not (mode=="udp_bound"):
                errors.append("UDP lifecycle treatment flag mismatch")
            for key in ("pre_send_ms","receive_ms","transport_elapsed_ms","post_bind_elapsed_ms","validation_ms","bind_ready_ms","socket_create_ms","bind_wait_ms","close_call_ms"):
                if key not in row:errors.append(f"Missing valid UDP timing stage {key}")
            if all(key in row for key in ("receive_ms","pre_send_ms","transport_elapsed_ms","post_bind_elapsed_ms","validation_ms")):
                if not np.isclose(row["receive_ms"]-row["pre_send_ms"],row["transport_elapsed_ms"],atol=1e-6,rtol=0):
                    errors.append("UDP send/receipt stage arithmetic mismatch")
                if not np.isclose(row["post_bind_elapsed_ms"],row["transport_elapsed_ms"]+row["validation_ms"],atol=1e-6,rtol=0):
                    errors.append("UDP post-bind validation arithmetic mismatch")
                if row["elapsed_ms"]+1e-6<row["post_bind_elapsed_ms"]+row["pre_send_ms"]:
                    errors.append("UDP whole-call duration shorter than constituent stages")
        else:
            if row.get("remote_port")!=443 or row.get("alpn")!="h2" or row.get("tls_session_reused") is not False:
                errors.append("Established H2 endpoint/ALPN/TLS-resumption mismatch")
            if row.get("connection_preexisting") is not True or row.get("http_status")!=200:
                errors.append("H2 established-session or HTTP-success mismatch")
            if row.get("tls_version") not in ("TLSv1.2","TLSv1.3"):errors.append("Unexpected TLS version")
            if not row.get("connection_id"):errors.append("Missing H2 connection identity")
    if len(grid)!=len(providers)*len(domains)*len(expected_windows)*len(expected_reps):
        errors.append("Measured matched-block grid mismatch")
    block_ids={}
    for key,block in grid.items():
        if set(block)!=expected_modes:errors.append(f"Incomplete treatment block {key}")
        elif {r.get("order") for r in block.values()}!={1,2,3}:errors.append("Invalid within-block randomized order")
        ids={r.get("block_id") for r in block.values()}
        if len(ids)!=1 or None in ids:errors.append("Inconsistent matched block identifiers")
        else:
            identifier=(key[1],next(iter(ids)))
            if identifier in block_ids and block_ids[identifier]!=key:errors.append("Block identifier reused across different matched blocks")
            block_ids[identifier]=key
    connections=[]
    for provider in sorted(providers):
        for window in sorted(expected_windows):
            for mode in ("udp_bound","doh_warm"):
                good=[r for r in records if r.get("provider")==provider and window_id(r["window"])==window and row_mode(r)==mode and r.get("valid") is True]
                ports=sorted(set(r.get("local_port") for r in good))
                ids=sorted(set(r.get("connection_id") for r in good)) if mode=="doh_warm" else []
                if len(ports)!=1:errors.append(f"Persistent {mode} local port changed {provider} window {window}")
                if mode=="doh_warm" and len(ids)!=1:errors.append(f"H2 connection identity changed {provider} window {window}")
                numbers=[r.get("connection_query_number") for r in good]
                if numbers!=sorted(set(numbers)):errors.append(f"Persistent query numbers not strictly increasing {provider} {window} {mode}")
                if mode=="doh_warm":
                    fingerprints={(r.get("connect_ms"),r.get("alpn"),r.get("tls_version"),r.get("remote_address")) for r in good}
                    if len(fingerprints)!=1:errors.append("H2 connection metadata changed within provider/window")
                connections.append({"provider":provider,"window":window,"protocol":mode,"successful_records":len(good),"distinct_local_ports":ports,"distinct_connection_ids":ids})
    declared=json.loads((directory/"design.json").read_text(encoding="utf-8-sig"))
    for key in ("windows","reps","interval_seconds","seed","domains","providers","modes","expected_measured_attempts","source_sha256"):
        if declared.get(key)!=env.get(key):errors.append(f"Runtime metadata differs from frozen design: {key}")
    sources={}
    for name,expected in declared["source_sha256"].items():
        archived=root/"docs/evidence/collection-source-2026-11-20"/name
        source=archived if archived.exists() else root/"scripts"/name
        actual=hashlib.sha256(source.read_bytes()).hexdigest()
        if actual!=expected:errors.append(f"Collector source hash mismatch: {name}")
        sources[name]={"sha256":actual,"source":str(source.relative_to(root))}
    plan_time=datetime.fromisoformat(plan["recorded_utc"])
    start=datetime.fromisoformat(env["started_utc"].replace("Z","+00:00"))
    before_start=plan_time<start
    if not before_start:errors.append("Frozen forecast did not precede collector start")
    if errors:raise ValueError("Control audit failed: "+"; ".join(sorted(set(errors))))
    return {"errors":[],"measured_records":len(measured),"priming_records":len(primers),
            "exact_complete_matched_blocks":len(grid),"persistent_connections":connections,
            "source_hashes":sources,"forecast_precedes_collector_start":before_start,
            "collector_started_utc":env["started_utc"],"frozen_plan_recorded_utc":plan["recorded_utc"],
            "notes":"Successful persistent UDP/H2 records retain exactly one local port per provider/window; H2 also retains one connection identity and unchanged metadata. Every successful wire response is independently decoded. Stage values are finite and nonnegative and UDP stage arithmetic is checked."}


def control_pairs(blocks, comparison, baseline, metric, date):
    out, failures = [], {"blocks":len(blocks), "both_attempted":0, "complete_pairs":0,
                         "missing_comparison":0, "missing_baseline":0, "both_failed":0,
                         "comparison_only_success":0, "baseline_only_success":0, "missing_metric":0}
    for key, block in sorted(blocks.items()):
        c, b = block.get(comparison), block.get(baseline)
        if c is None:failures["missing_comparison"]+=1
        if b is None:failures["missing_baseline"]+=1
        if c is None or b is None:continue
        failures["both_attempted"]+=1
        cv, bv = c.get("valid") is True, b.get("valid") is True
        if not cv or not bv:
            failures["both_failed"]+=not cv and not bv
            failures["comparison_only_success"]+=cv and not bv
            failures["baseline_only_success"]+=bv and not cv
            continue
        cvalue,bvalue = control_metric(c,metric),control_metric(b,metric)
        if cvalue is None or bvalue is None:
            failures["missing_metric"]+=1
            continue
        if not np.isfinite(cvalue) or not np.isfinite(bvalue) or cvalue<0 or bvalue<=0:
            raise ValueError(f"Invalid successful control metric {key} {metric}")
        out.append({"window":key[0], "window_key":f"{date}:w{key[0]}", "date":date,
                    "domain":key[1], "rep":key[2], "delta_ms":cvalue-bvalue,
                    "delta_pct":100*(cvalue-bvalue)/bvalue,
                    "comparison_ms":cvalue, "baseline_ms":bvalue,
                    "first_utc":min(c["started_utc"],b["started_utc"]),
                    "last_utc":max(c["started_utc"],b["started_utc"])})
    failures["complete_pairs"]=len(out)
    return out,failures


def control_analysis(root, directory):
    raw=directory/"control_raw.jsonl"
    if not raw.exists():
        return {"status":"not_available", "expected_directory":str(directory.relative_to(root))}
    env=json.loads((directory/"environment.json").read_text(encoding="utf-8-sig"))
    if env.get("status") != "complete":
        return {"status":"collection_incomplete", "expected_directory":str(directory.relative_to(root)),
                "note":"No outcome analysis is produced for a running collection."}
    records=read_jsonl(raw)
    measured=[r for r in records if r.get("phase")=="measure"]
    date=min(r["started_utc"] for r in measured)[:10]
    wire_checked=0
    for row in records:
        if row.get("valid") is True:
            if not decode_wire(row,row.get("domain"))["wire_valid"]:
                raise ValueError("Successful control response fails independent decoding")
            wire_checked+=1
    marginals, contrasts, windows, forecast, block_audits, port_diagnostics, baseline_swaps=[],[],[],[],[],[],[]
    plan=json.loads((root/"docs/control_analysis_plan.json").read_text(encoding="utf-8"))
    audit=control_audit(root,records,env,plan,directory)
    if plan["forecast_sign"] != 1:
        raise ValueError("Unexpected frozen forecast; review explicitly rather than silently changing the target")
    for provider in PROVIDERS:
        selected=[r for r in measured if r.get("provider")==provider]
        blocks=defaultdict(dict)
        for row in selected:
            key=(window_id(row["window"]),row["domain"],row["rep"])
            mode=row_mode(row)
            if mode in blocks[key]:raise ValueError(f"Duplicate control record {provider} {key} {mode}")
            blocks[key][mode]=row
        for window in sorted(set(k[0] for k in blocks)):
            common=[b for k,b in blocks.items() if k[0]==window and all(m in b and b[m].get("valid") is True for m in ("udp_fresh","udp_bound","doh_warm"))]
            if not common:continue
            fresh=[b["doh_warm"]["elapsed_ms"]-b["udp_fresh"]["elapsed_ms"] for b in common]
            bound=[b["doh_warm"]["elapsed_ms"]-b["udp_bound"]["elapsed_ms"] for b in common]
            shifts=[b["udp_fresh"]["elapsed_ms"]-b["udp_bound"]["elapsed_ms"] for b in common]
            mf,mb=med(fresh),med(bound)
            baseline_swaps.append({"provider":provider,"window":window,"common_complete_triplets":len(common),
                                   "doh_minus_fresh_median_ms":mf,"doh_minus_bound_median_ms":mb,
                                   "fresh_baseline_sign":sign(mf),"bound_baseline_sign":sign(mb),
                                   "strict_sign_flip":sign(mf)*sign(mb)==-1,"either_zero":mf==0 or mb==0,
                                   "difference_of_effect_medians_ms":mb-mf,
                                   "median_paired_udp_fresh_minus_bound_ms":med(shifts),
                                   "paired_identity_max_abs_error_ms":max(abs((b-a)-shift) for a,b,shift in zip(fresh,bound,shifts))})
        for mode in ("udp_fresh","udp_bound","doh_warm"):
            group=[r for r in selected if row_mode(r)==mode]
            for metric in ("elapsed_ms","transport_elapsed_ms","post_bind_query_ms","socket_create_ms","bind_wait_ms","bind_ready_ms","pre_send_ms","validation_ms","close_call_ms"):
                good=[r for r in group if r.get("valid") is True and control_metric(r,metric) is not None]
                if good:
                    marginals.append({"provider":provider,"mode":mode,"metric":metric,
                                      "attempts":len(group),"successful":sum(r.get("valid") is True for r in group),
                                      **describe(control_metric(r,metric) for r in good)})
            for window in sorted(set(window_id(r["window"]) for r in group)):
                local=[r for r in group if window_id(r["window"])==window and r.get("valid") is True]
                ports=sorted(set(r.get("local_port") for r in local if r.get("local_port") is not None))
                port_diagnostics.append({"provider":provider,"mode":mode,"window":window,
                                         "successful_records":len(local),"unique_local_port_count":len(ports),
                                         "local_ports":";".join(map(str,ports))})
        specs=[("udp_fresh","udp_bound","elapsed_ms"),
               ("udp_fresh","udp_bound","transport_elapsed_ms"),
               ("udp_fresh","udp_bound","post_bind_query_ms"),
               ("doh_warm","udp_bound","elapsed_ms"),
               ("doh_warm","udp_fresh","elapsed_ms")]
        for comparison,baseline,metric in specs:
            pairs,counts=control_pairs(blocks,comparison,baseline,metric,date)
            meta={"provider":provider,"comparison":comparison,"baseline":baseline,"metric":metric}
            block_audits.append({**meta,**counts})
            if not pairs:continue
            ws=window_summaries(pairs,meta)
            windows.extend(ws)
            contrasts.append(aggregate(pairs,ws,meta))
            if provider=="google" and comparison=="doh_warm" and baseline=="udp_fresh" and metric=="elapsed_ms":
                for w in ws:
                    belonging=[p for p in pairs if p["window_key"]==w["window_key"]]
                    first=min(p["first_utc"] for p in belonging)
                    forecast.append({"window":w["window"],"window_key":w["window_key"],"complete_pairs":w["n"],
                                     "forecast_sign":1,"observed_median_ms":w["median_ms"],
                                     "observed_sign":w["median_sign"],"sign_agrees":w["median_sign"]==1,
                                     "first_measured_pair_utc":first,
                                     "plan_precedes_window_observations":datetime.fromisoformat(plan["recorded_utc"])<datetime.fromisoformat(first.replace("Z","+00:00"))})
    forecast_summary={"frozen_plan_recorded_utc":plan["recorded_utc"],"target":plan["forecast_target"],
                      "windows_evaluated":len(forecast),"positive_sign_matches":sum(f["sign_agrees"] for f in forecast),
                      "zero_or_opposite_sign":sum(not f["sign_agrees"] for f in forecast),
                      "plan_precedes_all_evaluated_windows":all(f["plan_precedes_window_observations"] for f in forecast),
                      "observed_window_median_min_ms":min((f["observed_median_ms"] for f in forecast),default=None),
                      "observed_window_median_max_ms":max((f["observed_median_ms"] for f in forecast),default=None),
                      "observations":forecast,
                      "caveat":plan["implementation_caveat"]}
    swap_summary=[]
    for provider in PROVIDERS:
        selected=[s for s in baseline_swaps if s["provider"]==provider]
        shifts=[s["difference_of_effect_medians_ms"] for s in selected]
        paired_shifts=[s["median_paired_udp_fresh_minus_bound_ms"] for s in selected]
        swap_summary.append({"provider":provider,"windows":len(selected),"strict_sign_flip_count":sum(s["strict_sign_flip"] for s in selected),
                             "either_zero_count":sum(s["either_zero"] for s in selected),
                             "difference_of_window_effect_medians_range_ms":[min(shifts),max(shifts)] if shifts else [],
                             "median_paired_baseline_shift_range_ms":[min(paired_shifts),max(paired_shifts)] if paired_shifts else [],
                             "note":"Every window uses the same complete three-treatment matched blocks. Difference of two window effect medians is not the median of paired baseline shifts. At individual matched-block level, (DoH−bound)−(DoH−fresh)=fresh−bound."})
    return {"status":"complete","date":date,"data_directory":str(directory.relative_to(root)),
            "total_records":len(records),"measured_attempts":len(measured),
            "failed_measured_attempts":sum(r.get("valid") is not True for r in measured),
            "independent_wire_rechecks":wire_checked,"marginals":marginals,"paired_contrasts":contrasts,
            "validation":audit,"environment":{"platform":env["platform"],"release":env["release"],"node":env["node"],"openssl":env["openssl"]},
            "windows":windows,"pairing_audits":block_audits,"port_diagnostics":port_diagnostics,
            "baseline_swap_windows":baseline_swaps,"baseline_swap_summary":swap_summary,
            "forecast_validation":forecast_summary,
            "timing_scope":"elapsed_ms is the reported whole measured call: fresh UDP includes explicit create/bind; bound UDP and established DoH exclude already completed setup. transport_elapsed_ms is the common UDP send-call-to-receipt stage after bind, excluding validation. post_bind_query_ms is used only if explicitly recorded, never guessed from undocumented stage offsets. Persistent source-port/network/cache affinity and different protocol libraries remain alternative explanations."}


def csv_write(path, rows):
    if not rows:return
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in row.items()})


def write_report(root,result):
    h=result["historical"]
    lines=["# Window sensitivity and UDP lifecycle control", "", "Generated from retained actual measurements. Historical and explicit-bind control estimands remain separate.", "", "## Historical six-window sensitivity", "", "| Provider | Contrast | Pooled paired median ms | Fixed-window conditional interval ms | Median of window medians ms | Window range ms | Positive / negative windows |", "|---|---|---:|---|---:|---|---|"]
    for r in h["pooled_contrasts"]:
        lo,hi=r["conditional_fixed_window_interval_ms"]
        lines.append(f"| {r['provider']} | {r['comparison']} − UDP | {r['pooled_median_ms']:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {r['median_of_window_medians_ms']:+.3f} | [{r['window_median_min_ms']:+.3f}, {r['window_median_max_ms']:+.3f}] | {r['positive_window_count']} / {r['negative_window_count']} |")
    lines += ["", h["scope"], "", "The interval holds the six selected windows fixed and does not estimate uncertainty across a population of network conditions. A narrow interval can coexist with a reversal of window-level sign.", "", "## Retrospective held-window check", ""]
    for r in h["pooled_contrasts"]:
        lines.append(f"- {r['provider']} {r['comparison']}: training on the other five windows predicted the held window median's sign in {r['retrospective_leave_window_sign_agrees']}/{r['retrospective_leave_window_checks']} cases; mean absolute point-prediction error {r['retrospective_leave_window_mae_ms']:.3f} ms versus {r['retrospective_zero_adjustment_mae_ms']:.3f} ms for a zero-adjustment forecast. These errors target window medians, not individual query times.")
    c=result["control"]
    lines += ["", "## Follow-up control", "", f"Status: {c['status']}."]
    if c["status"]=="complete":
        lines += ["", f"Measured attempts: {c['measured_attempts']}; failed: {c['failed_measured_attempts']}; independently decoded valid records including priming: {c['independent_wire_rechecks']}.", "", "| Provider | Comparison − baseline | Metric | Complete pairs | Pooled median ms | Window range ms | Positive / negative windows |", "|---|---|---|---:|---:|---|---|"]
        for r in c["paired_contrasts"]:
            lines.append(f"| {r['provider']} | {r['comparison']} − {r['baseline']} | {r['metric']} | {r['complete_pairs']} | {r['pooled_median_ms']:+.3f} | [{r['window_median_min_ms']:+.3f}, {r['window_median_max_ms']:+.3f}] | {r['positive_window_count']} / {r['negative_window_count']} |")
        f=c["forecast_validation"]
        lines += ["", "## Frozen Google sign check", "", f"The frozen positive-sign forecast matched {f['positive_sign_matches']}/{f['windows_evaluated']} observed window medians; zero or opposite-sign medians: {f['zero_or_opposite_sign']}. The plan preceded every evaluated window: {f['plan_precedes_all_evaluated_windows']}.", "", f["caveat"], "", c["timing_scope"]]
        lines += ["", "## Replacing the UDP baseline within each window", ""]
        for s in c["baseline_swap_summary"]:
            low,high=s["difference_of_window_effect_medians_range_ms"]
            paired_low,paired_high=s["median_paired_baseline_shift_range_ms"]
            lines.append(f"- {s['provider']}: strict sign reversal in {s['strict_sign_flip_count']}/{s['windows']} windows; {s['either_zero_count']} windows have an exactly zero effect under at least one baseline. The difference of window effect medians ranges from {low:+.3f} to {high:+.3f} ms. The separate median paired fresh-minus-bound UDP shift ranges from {paired_low:+.3f} to {paired_high:+.3f} ms.")
        lines += ["", "All baseline-swap comparisons use the same complete three-treatment blocks within each window. The difference of effect medians must not be called the median paired shift. The per-block identity is (DoH − bound UDP) − (DoH − fresh UDP) = fresh UDP − bound UDP."]
    lines += ["", "## Interpretation boundaries", "", "No p-values or population confidence guarantees are used. Conditional resampling does not correct shared time effects, resolver-cache uncertainty or routing bias. Persistent UDP source ports may change network/cache affinity, so the fresh-versus-bound comparison does not isolate local CPU lifecycle cost. All successful values remain; failures are retained separately; no trimming or imputation occurs.", ""]
    (root/"docs/CONTROL_RESULTS.md").write_text("\n".join(lines),encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--control-dir",type=Path,default=Path("data/control-2026-11-20"))
    args=parser.parse_args()
    root=args.root.resolve()
    control_dir=args.control_dir if args.control_dir.is_absolute() else root/args.control_dir
    frozen_checks=verify_frozen_history(root)
    result={"generated_utc":datetime.now(timezone.utc).isoformat(),"seed":SEED,"numpy_version":np.__version__,"conditional_resamples":RESAMPLES,
            "conditional_resampling_scope":"Resample successful matched paired blocks within each fixed observed window, retaining all window sample sizes. This descriptive calculation assumes exchangeability of these paired blocks and does not model serial/domain dependence; its interval can be too narrow. It does not estimate network/day population coverage.",
            "frozen_historical_input_hashes_verified":frozen_checks,
            "historical":historical_analysis(root),"control":control_analysis(root,control_dir)}
    out=root/"results"
    (out/"control_analysis.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    for key in ("pooled_contrasts","windows","held_window_checks","date_holdouts"):
        csv_write(out/f"historical_{key}.csv",result["historical"][key])
    if result["control"]["status"]=="complete":
        for key in ("marginals","paired_contrasts","windows","pairing_audits","port_diagnostics","baseline_swap_windows","baseline_swap_summary"):
            csv_write(out/f"control_{key}.csv",result["control"][key])
        csv_write(out/"google_forecast_validation.csv",result["control"]["forecast_validation"]["observations"])
    write_report(root,result)
    print(json.dumps({"historical_contrasts":len(result["historical"]["pooled_contrasts"]),"control_status":result["control"]["status"],"output":"results/control_analysis.json"}))


if __name__=="__main__":
    main()
