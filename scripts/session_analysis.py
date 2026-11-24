"""Analyze the locally frozen same-evening session extension.

Running/missing sessions remain explicit status records and their outcome files
are never opened. Only completed audited sessions contribute observations.
"""
from __future__ import annotations

import argparse
import base64
from collections import defaultdict
import csv
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

import numpy as np

from analyze import decode_wire
from control_analysis import control_pairs, describe, med, sign
from robustness import read_jsonl, window_id

PLAN_PATH = "docs/SESSION_EXTENSION_PLAN.json"
FORECAST_ARCHIVE = "docs/evidence/session-calibration-2026-11-22/control_analysis.json"
NEW_SOURCE = "docs/evidence/collection-source-2026-11-22"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def category(value, threshold):
    return "above_positive_threshold" if value > threshold else "below_negative_threshold" if value < -threshold else "inside_threshold_band"


def metric_stats(values):
    a=np.asarray(list(values), dtype=float)
    if not len(a):
        return {"complete_pairs":0,"median_delta_ms":None,"median_abs_delta_ms":None,"abs_median_delta_ms":None,"q1_delta_ms":None,"q3_delta_ms":None,"min_delta_ms":None,"max_delta_ms":None}
    q1,median,q3=np.quantile(a,[.25,.5,.75])
    return {"complete_pairs":len(a),"median_delta_ms":float(median),"median_abs_delta_ms":float(np.median(np.abs(a))),
            "abs_median_delta_ms":float(abs(median)),"q1_delta_ms":float(q1),"q3_delta_ms":float(q3),
            "min_delta_ms":float(a.min()),"max_delta_ms":float(a.max()),
            "positive_pairs":int(np.count_nonzero(a>0)),"negative_pairs":int(np.count_nonzero(a<0)),"zero_pairs":int(np.count_nonzero(a==0))}


def threshold_rates(pairs, meta, thresholds):
    values=np.asarray([p["delta_ms"] for p in pairs],dtype=float)
    out=[]
    for t in thresholds:
        below=int(np.count_nonzero(values < -t)); above=int(np.count_nonzero(values > t))
        inside=len(values)-below-above
        outside=np.abs(values[np.abs(values)>t])
        out.append({**meta,"threshold_ms":t,"complete_pairs":len(values),
                    "below_negative_count":below,"inside_band_count":inside,"above_positive_count":above,
                    "fraction_below_negative":below/len(values) if len(values) else None,
                    "fraction_inside_band":inside/len(values) if len(values) else None,
                    "fraction_above_positive":above/len(values) if len(values) else None,
                    "fraction_abs_gt_threshold":(below+above)/len(values) if len(values) else None,
                    "median_abs_delta_outside_band_ms":med(outside)})
    return out


def check_stages(row):
    """Return corruption reasons without turning malformed data into results."""
    errors=[]
    for key,value in row.items():
        if key.endswith("_ms") and value is not None:
            if not isinstance(value,(int,float)) or not np.isfinite(value) or value<0:
                errors.append(f"Invalid nonnegative stage {key}")
    if row.get("valid") is True and row.get("protocol","").startswith("udp_"):
        required=("pre_send_ms","receive_ms","transport_elapsed_ms","post_bind_elapsed_ms","validation_ms","bind_ready_ms","socket_create_ms","bind_wait_ms","close_call_ms","elapsed_ms")
        if any(k not in row for k in required):
            errors.append("Missing successful UDP stage")
        else:
            if not np.isclose(row["receive_ms"]-row["pre_send_ms"],row["transport_elapsed_ms"],atol=1e-6,rtol=0):errors.append("UDP transport-stage arithmetic mismatch")
            if not np.isclose(row["transport_elapsed_ms"]+row["validation_ms"],row["post_bind_elapsed_ms"],atol=1e-6,rtol=0):errors.append("UDP validated-stage arithmetic mismatch")
            if row["elapsed_ms"]+1e-6 < row["pre_send_ms"]+row["post_bind_elapsed_ms"]:errors.append("UDP whole-call shorter than measured stages")
    return errors


def audit_session(root, planned, plan, env, rows):
    errors=[]; modes=set(plan["modes"]); domains=set(plan["domains"]); providers=set(plan["providers"])
    for key in ("windows","reps","interval_seconds","seed"):
        if env.get(key)!=planned[key]:errors.append(f"Design mismatch {key}")
    if env.get("source_sha256")!=plan["maintained_source_sha256"]:errors.append("Collection source differs from frozen maintained protocol")
    if utc(env["started_utc"])<=utc(plan["recorded_utc"]):errors.append("Collection preceded frozen plan")
    if set(env.get("domains",[]))!=domains or set(env.get("providers",{}))!=providers or set(env.get("modes",[]))!=modes:errors.append("Domain/provider/treatment design mismatch")
    measured=[r for r in rows if r.get("phase")=="measure"]; primes=[r for r in rows if r.get("phase")=="prime"]
    if len(measured)!=planned["expected_measured_attempts"]:errors.append("Measured count differs from planned complete grid")
    if len(primes)!=planned["expected_priming_records"]:errors.append("Priming count differs from planned grid")
    if len(rows)!=len(measured)+len(primes):errors.append("Unknown record phase")
    grid=defaultdict(dict); prime_keys=set(); ids=set(); wire_checks=0
    for row in rows:
        provider,domain,mode=row.get("provider"),row.get("domain"),row.get("protocol")
        w=window_id(row["window"])
        if provider not in providers or domain not in domains or mode not in modes or not 1<=w<=planned["windows"]:
            errors.append("Record outside declared grid");continue
        if row.get("phase")=="measure":
            rep=row.get("rep")
            if not isinstance(rep,int) or not 1<=rep<=planned["reps"]:errors.append("Unexpected repetition")
            key=(provider,w,domain,rep)
            if mode in grid[key]:errors.append("Duplicate measured mode")
            grid[key][mode]=row
        elif row.get("phase")=="prime":
            key=(provider,w,domain,mode)
            if key in prime_keys:errors.append("Duplicate primer")
            prime_keys.add(key)
        errors.extend(check_stages(row))
        try:
            query=base64.b64decode(row["query_base64"],validate=True)
            identity=int.from_bytes(query[:2],"big")
            if identity in ids:errors.append("Repeated transaction ID within session")
            ids.add(identity)
            if row.get("valid") is True:
                if not decode_wire(row,domain)["wire_valid"]:errors.append("Saved successful DNS response fails independent decoder")
                wire_checks+=1
        except (KeyError,ValueError,TypeError) as error:
            errors.append(f"Wire audit failed: {error}")
        if row.get("valid") is not True:continue
        if row.get("remote_address")!=env["providers"][provider]["ip"]:errors.append("Provider destination mismatch")
        if not isinstance(row.get("local_port"),int) or not 0<row["local_port"]<65536:errors.append("Invalid local port")
        if mode.startswith("udp_"):
            if row.get("remote_port")!=53 or row.get("udp_connected") is not False or row.get("bound_before_timing") is not (mode=="udp_bound"):errors.append("UDP endpoint/lifecycle flags mismatch")
        else:
            if row.get("remote_port")!=443 or row.get("alpn")!="h2" or row.get("tls_session_reused") is not False or row.get("connection_preexisting") is not True or row.get("http_status")!=200:errors.append("Established H2/TLS treatment mismatch")
    expected_blocks=2*planned["windows"]*len(domains)*planned["reps"]
    if len(grid)!=expected_blocks:errors.append("Matched grid count mismatch")
    for block in grid.values():
        if set(block)!=modes or {r.get("order") for r in block.values()}!={1,2,3}:errors.append("Incomplete/randomized block mismatch")
        if len({r.get("block_id") for r in block.values()})!=1:errors.append("Inconsistent block IDs")
    connections=[]
    for provider in sorted(providers):
        for w in range(1,planned["windows"]+1):
            for mode in ("udp_bound","doh_warm"):
                selected=[r for r in rows if r.get("provider")==provider and window_id(r["window"])==w and r.get("protocol")==mode and r.get("valid") is True]
                ports=set(r.get("local_port") for r in selected)
                if len(ports)!=1:errors.append(f"Persistent port mismatch {provider}/{w}/{mode}")
                numbers=[r.get("connection_query_number") for r in selected]
                if numbers!=sorted(set(numbers)):errors.append("Persistent query sequence mismatch")
                if mode=="doh_warm":
                    fingerprints={(r.get("connection_id"),r.get("connect_ms"),r.get("alpn"),r.get("tls_version"),r.get("remote_address")) for r in selected}
                    if len(fingerprints)!=1:errors.append("Persistent H2 identity changed")
                connections.append({"provider":provider,"window":w,"protocol":mode,"distinct_port_count":len(ports),"successful_records":len(selected)})
    return {"errors":sorted(set(errors)),"raw_records":len(rows),"measured_attempts":len(measured),"priming_records":len(primes),
            "failed_measured_attempts":sum(r.get("valid") is not True for r in measured),"independent_wire_rechecks":wire_checks,
            "failed_measurements":[{k:r.get(k) for k in ("provider","protocol","domain","window","rep","started_utc","elapsed_ms","error")} for r in measured if r.get("valid") is not True],
            "complete_matched_blocks":len(grid),"persistent_connections":connections,"raw_sha256":sha(root/planned["directory"]/"control_raw.jsonl")}


def fingerprint(env):
    fields={k:env.get(k) for k in ("source_sha256","platform","release","arch","node","openssl","cpu_model","logical_cpus","providers","domains","modes","qtype","ip_version")}
    digest=hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest()[:16]
    return digest,fields


def load_session(root, planned, plan):
    """Early status checks deliberately precede opening any outcome records."""
    directory=root/planned["directory"]
    status={"session_id":planned["session_id"],"directory":planned["directory"],"scheduled_start_utc":planned["scheduled_start_utc"],
            "actual_start_utc":None,"actual_finish_utc":None,"status":"missing","build_group":None,"audit":None}
    if not directory.exists():return status,None
    if not (directory/"environment.json").exists():
        status["status"]="metadata_missing";return status,None
    try:env=json.loads((directory/"environment.json").read_text(encoding="utf-8-sig"))
    except (OSError,json.JSONDecodeError) as error:
        status.update(status="metadata_unreadable",reason=str(error));return status,None
    status["actual_start_utc"]=env.get("started_utc")
    status["actual_finish_utc"]=env.get("finished_utc")
    if status["actual_start_utc"]:
        status["scheduled_start_delay_seconds"]=(utc(status["actual_start_utc"])-utc(planned["scheduled_start_utc"])).total_seconds()
    if env.get("status")!="complete":
        status["status"]="running" if env.get("status")=="running" else "not_complete"
        status["reported_collection_status"]=env.get("status")
        return status,None
    if not (directory/"control_raw.jsonl").exists():
        status.update(status="invalid",reason="Complete metadata without raw observations");return status,None
    try:
        rows=read_jsonl(directory/"control_raw.jsonl")
        audit=audit_session(root,planned,plan,env,rows)
        if (directory/"session_metadata.json").exists():
            ledger=json.loads((directory/"session_metadata.json").read_text(encoding="utf-8-sig"))
            if ledger.get("plan_sha256")!=sha(root/PLAN_PATH):audit["errors"].append("Session ledger frozen-plan hash mismatch")
            if ledger.get("source_sha256")!=plan["maintained_source_sha256"]:audit["errors"].append("Session ledger source mismatch")
            status["session_metadata"]="session_metadata.json"
            status["network_observation_files"]=ledger.get("network_observation_files",[])
        status["audit"]=audit
        if audit["errors"]:
            status["status"]="invalid";return status,None
    except (OSError,ValueError,KeyError,TypeError) as error:
        status.update(status="invalid",reason=str(error));return status,None
    group,fields=fingerprint(env)
    status.update(status="complete",build_group=group,environment_fingerprint=fields)
    status["actual_finish_utc"]=env.get("finished_utc") or max(r["started_utc"] for r in rows)
    status["duration_boundary_note"]="Collector finish timestamp" if env.get("finished_utc") else "Last attempt start; finish unavailable"
    return status,{"rows":rows,"env":env,"status":status}


def verify_plan(root,plan):
    calibration=root/"data/control-2026-11-20/control_raw.jsonl"
    if sha(calibration)!=plan["calibration"]["raw_sha256"]:raise ValueError("Nov20 whole raw file differs from frozen calibration")
    archive=root/FORECAST_ARCHIVE
    if sha(archive)!=plan["calibration"]["analysis_sha256"]:raise ValueError("Frozen calibration analysis snapshot changed")
    sources={}
    for name,expected in plan["maintained_source_sha256"].items():
        archived=root/NEW_SOURCE/name
        source=archived if archived.exists() else root/"scripts"/name
        if sha(source)!=expected:raise ValueError(f"Maintained collection source mismatch: {name}")
        sources[name]={"sha256":expected,"verified_path":source.relative_to(root).as_posix()}
    old=json.loads(archive.read_text(encoding="utf-8"))
    current_source=root/NEW_SOURCE/"measure_controls.mjs"
    if not current_source.exists():current_source=root/"scripts/measure_controls.mjs"
    old_source=root/"docs/evidence/collection-source-2026-11-20/measure_controls.mjs"
    diff=list(difflib.unified_diff(old_source.read_text(encoding="utf-8-sig").splitlines(),current_source.read_text(encoding="utf-8-sig").splitlines(),fromfile="Nov20 snapshot",tofile="Nov22 maintained collector",lineterm=""))
    return {"plan_sha256":sha(root/PLAN_PATH),"recorded_utc":plan["recorded_utc"],"calibration_raw_sha256_verified":plan["calibration"]["raw_sha256"],
            "calibration_analysis_archive":FORECAST_ARCHIVE,"maintained_sources":sources,"collector_diff_from_calibration":diff,
            "supporting_module_identical_to_calibration":plan["maintained_source_sha256"]["dns_client.mjs"]==plan["calibration"]["source_sha256"]["dns_client.mjs"]},old


def analyze(root):
    plan=json.loads((root/PLAN_PATH).read_text(encoding="utf-8"))
    validation,reference=verify_plan(root,plan)
    statuses=[];loaded=[]
    for planned in plan["sessions"]:
        status,data=load_session(root,planned,plan)
        statuses.append(status)
        if data is not None:loaded.append(data)
    effects=[];windows=[];marginals=[];rates=[];session_decisions=[];window_decisions=[]
    pairing_audits=[];forecast_rows=[];prospective_decisions=[]
    for ds in loaded:
        sid=ds["status"]["session_id"];group=ds["status"]["build_group"]
        date=ds["env"]["started_utc"][:10]
        measured=[r for r in ds["rows"] if r["phase"]=="measure"]
        for provider in plan["providers"]:
            selected=[r for r in measured if r["provider"]==provider]
            blocks=defaultdict(dict)
            for r in selected:blocks[(window_id(r["window"]),r["domain"],r["rep"])][r["protocol"]]=r
            for mode in plan["modes"]:
                for w in [None]+list(range(1,ds["env"]["windows"]+1)):
                    own=[r for r in selected if r["protocol"]==mode and (w is None or window_id(r["window"])==w)]
                    for metric in ("elapsed_ms","post_bind_elapsed_ms","transport_elapsed_ms","bind_ready_ms","validation_ms"):
                        valid=[r for r in own if r.get("valid") is True and isinstance(r.get(metric),(int,float))]
                        if valid:marginals.append({"session_id":sid,"build_group":group,"provider":provider,"protocol":mode,"window":w,
                                                   "metric":metric,"attempted":len(own),"successful":sum(r.get("valid") is True for r in own),
                                                   **describe(r[metric] for r in valid)})
            for spec in plan["contrast_specs"]:
                comparison,baseline,metric=spec["comparison"],spec["baseline"],spec["metric"]
                pairs,counts=control_pairs(blocks,comparison,baseline,metric,date)
                key={"session_id":sid,"build_group":group,"provider":provider,"comparison":comparison,"baseline":baseline,"metric":metric}
                pairing_audits.append({**key,**counts})
                if not pairs:continue
                effect={**key,**metric_stats(p["delta_ms"] for p in pairs)}
                effect["fraction_abs_gt_2ms"]=sum(abs(p["delta_ms"])>2 for p in pairs)/len(pairs)
                own_windows=[]
                for w in sorted(set(p["window"] for p in pairs)):
                    subset=[p for p in pairs if p["window"]==w]
                    wm={**key,"window":w,**metric_stats(p["delta_ms"] for p in subset)}
                    own_windows.append(wm);windows.append(wm)
                    rates.extend(threshold_rates(subset,{**key,"level":"window","window":w},plan["thresholds_ms"]))
                    for t in plan["thresholds_ms"]:window_decisions.append({**key,"window":w,"threshold_ms":t,"category":category(wm["median_delta_ms"],t)})
                effect.update(window_median_min_ms=min(w["median_delta_ms"] for w in own_windows),window_median_max_ms=max(w["median_delta_ms"] for w in own_windows),
                              median_of_window_medians_ms=med(w["median_delta_ms"] for w in own_windows),observed_windows=len(own_windows))
                effects.append(effect)
                rates.extend(threshold_rates(pairs,{**key,"level":"session","window":None},plan["thresholds_ms"]))
                for t in plan["thresholds_ms"]:session_decisions.append({**key,"threshold_ms":t,"category":category(effect["median_delta_ms"],t)})
                forecasts=[f for f in plan["calibration"]["forecasts_for_each_new_session"] if all(f[k]==key[k] for k in ("provider","comparison","baseline","metric"))]
                if forecasts:
                    f=forecasts[0];point=f["calibration_point_ms"];actual=effect["median_delta_ms"]
                    forecast_rows.append({**key,"forecast_point_ms":point,"actual_median_ms":actual,"actual_median_abs_delta_ms":effect["median_abs_delta_ms"],
                                          "forecast_sign":f["predicted_sign"],"actual_sign":sign(actual),"sign_agrees":f["predicted_sign"]==sign(actual),
                                          "absolute_prediction_error_ms":abs(point-actual),"zero_adjustment_error_ms":abs(actual),
                                          "frozen_before_session":utc(plan["recorded_utc"])<utc(ds["env"]["started_utc"])})
                    for fc in f["threshold_categories"]:
                        prospective_decisions.append({**key,"threshold_ms":fc["threshold_ms"],"forecast_category":fc["category"],"actual_category":category(actual,fc["threshold_ms"]),
                                                      "category_agrees":fc["category"]==category(actual,fc["threshold_ms"])})
    groups=[];leave=[];leave_decisions=[]
    for group in sorted(set(s["build_group"] for s in statuses if s["status"]=="complete")):
        member=[s["session_id"] for s in statuses if s["status"]=="complete" and s["build_group"]==group]
        ge=[e for e in effects if e["build_group"]==group]
        summaries=[]
        for provider in plan["providers"]:
            for spec in plan["contrast_specs"]:
                own=[e for e in ge if e["provider"]==provider and all(e[k]==spec[k] for k in ("comparison","baseline","metric"))]
                if not own:continue
                values=[e["median_delta_ms"] for e in own]
                summaries.append({"provider":provider,**{k:spec[k] for k in ("comparison","baseline","metric")},"session_count":len(own),
                                  "equal_session_median_ms":med(values),"session_median_min_ms":min(values),"session_median_max_ms":max(values),
                                  "positive_session_count":sum(x>0 for x in values),"negative_session_count":sum(x<0 for x in values),"zero_session_count":sum(x==0 for x in values)})
                if len(own)<3:continue
                for held in own:
                    training=[e["median_delta_ms"] for e in own if e["session_id"]!=held["session_id"]]
                    prediction=med(training);actual=held["median_delta_ms"]
                    lk={k:held[k] for k in ("session_id","build_group","provider","comparison","baseline","metric")}
                    leave.append({**lk,"training_sessions":len(training),"predicted_median_ms":prediction,"held_median_ms":actual,
                                  "sign_agrees":sign(prediction)==sign(actual),"absolute_prediction_error_ms":abs(prediction-actual),"zero_adjustment_error_ms":abs(actual)})
                    for t in plan["thresholds_ms"]:leave_decisions.append({**lk,"threshold_ms":t,"predicted_category":category(prediction,t),"held_category":category(actual,t),"category_agrees":category(prediction,t)==category(actual,t)})
        groups.append({"build_group":group,"session_ids":member,"session_count":len(member),"effects":summaries,
                       "leave_session_status":"available_retrospective" if len(member)>=3 else "insufficient_sessions_requires_three"})
    prospective=[]
    for f in plan["calibration"]["forecasts_for_each_new_session"]:
        key={k:f[k] for k in ("provider","comparison","baseline","metric")}
        own=[r for r in forecast_rows if all(r[k]==v for k,v in key.items())]
        scores=[]
        for t in plan["thresholds_ms"]:
            d=[r for r in prospective_decisions if r["threshold_ms"]==t and all(r[k]==v for k,v in key.items())]
            scores.append({"threshold_ms":t,"matches":sum(r["category_agrees"] for r in d),"evaluated":len(d)})
        prospective.append({**key,"forecast_point_ms":f["calibration_point_ms"],"session_count":len(own),"forecast_mae_ms":float(np.mean([r["absolute_prediction_error_ms"] for r in own])) if own else None,
                            "zero_adjustment_mae_ms":float(np.mean([r["zero_adjustment_error_ms"] for r in own])) if own else None,
                            "sign_matches":sum(r["sign_agrees"] for r in own),"threshold_category_scores":scores})
    leave_summary=[]
    for group in groups:
        for provider in plan["providers"]:
            for spec in plan["contrast_specs"]:
                key={"build_group":group["build_group"],"provider":provider,**{k:spec[k] for k in ("comparison","baseline","metric")}}
                own=[r for r in leave if all(r[k]==v for k,v in key.items())]
                if not own:continue
                scores=[]
                for t in plan["thresholds_ms"]:
                    decisions=[r for r in leave_decisions if r["threshold_ms"]==t and all(r[k]==v for k,v in key.items())]
                    scores.append({"threshold_ms":t,"matches":sum(r["category_agrees"] for r in decisions),"evaluated":len(decisions)})
                leave_summary.append({**key,"held_sessions":len(own),"forecast_mae_ms":float(np.mean([r["absolute_prediction_error_ms"] for r in own])),
                                      "zero_adjustment_mae_ms":float(np.mean([r["zero_adjustment_error_ms"] for r in own])),"sign_matches":sum(r["sign_agrees"] for r in own),
                                      "threshold_category_scores":scores,"scope":"Retrospective leave-session check, not an issued prospective forecast or population validation."})
    covariation=google_covariation(marginals,windows)
    completed=[s for s in statuses if s["status"]=="complete"]
    chronology={"planned_sessions":len(statuses),"completed_sessions":len(completed),"is_final":len(completed)==len(statuses),
                "actual_utc_dates":sorted(set(s["actual_start_utc"][:10] for s in completed)),"starts_and_finishes":[{k:s[k] for k in ("session_id","actual_start_utc","actual_finish_utc")} for s in completed],"gaps_seconds":[]}
    for previous,current in zip(completed,completed[1:]):
        gap=(utc(current["actual_start_utc"])-utc(previous["actual_finish_utc"])).total_seconds()
        chronology["gaps_seconds"].append({"previous":previous["session_id"],"next":current["session_id"],"finish_to_start_seconds":gap,
                                          "start_to_start_seconds":(utc(current["actual_start_utc"])-utc(previous["actual_start_utc"])).total_seconds(),"overlap":gap<0})
    return {"generated_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"schema_version":1,"numpy_version":np.__version__,
            "analysis_status":"complete" if chronology["is_final"] else "partial","plan_validation":validation,"sessions":statuses,"chronology":chronology,
            "build_groups":groups,"session_effects":effects,"window_effects":windows,"marginals":marginals,"pairing_audits":pairing_audits,
            "thresholds":{"values_ms":plan["thresholds_ms"],"paired_rates":rates,"window_decisions":window_decisions,"session_decisions":session_decisions,
                          "interpretation":"Sensitivity bands, not validated utility/equivalence thresholds. Paired-observation rates and categories of window/session medians have different denominators and estimands."},
            "prospective_forecasts":forecast_rows,"prospective_decisions":prospective_decisions,"prospective_summary":prospective,
            "leave_session_checks":leave,"leave_session_decisions":leave_decisions,"leave_session_summary":leave_summary,"exploratory_google_covariation":covariation,
            "reference":{"date":"2026-11-20","calibration_forecasts":plan["calibration"]["forecasts_for_each_new_session"],
                         "legacy_positive_google_forecast":reference["control"]["forecast_validation"],
                         "note":"Historical samples remain separate references. No old/new pooled query estimate is reported."},
            "interpretation":"Selected same-evening sessions; no multi-day or network population claim. No across-session confidence/equivalence interval. Within-session paired observations share domains/windows; rates describe retained successful pairs only. Cache/routing/source-port and unobserved conditions prevent mechanism attribution."}


def google_covariation(marginals,windows):
    out=[]
    for group in sorted(set(r["build_group"] for r in marginals)):
        selected=[r for r in marginals if r["build_group"]==group and r["provider"]=="google" and r["metric"]=="elapsed_ms" and r["window"] is not None]
        cells=defaultdict(dict)
        for r in selected:cells[(r["session_id"],r["window"])][r["protocol"]]=r["median_ms"]
        points=[]
        for (sid,w),values in sorted(cells.items()):
            if not all(m in values for m in ("doh_warm","udp_fresh","udp_bound")):continue
            point={"session_id":sid,"window":w,**{m+"_median_ms":values[m] for m in values}}
            for mode in ("doh_warm","udp_fresh","udp_bound"):
                marginal=next(r for r in selected if r["session_id"]==sid and r["window"]==w and r["protocol"]==mode)
                point[mode+"_successful_count"]=marginal["successful"]
                point[mode+"_attempted_count"]=marginal["attempted"]
            own=[v for (s,_),v in cells.items() if s==sid]
            for mode in ("doh_warm","udp_fresh","udp_bound"):
                point[mode+"_centered_ms"]=values[mode]-med(v[mode] for v in own if mode in v)
            for baseline in ("udp_fresh","udp_bound"):
                found=[r for r in windows if r["build_group"]==group and r["provider"]=="google" and r["session_id"]==sid and r["window"]==w and r["comparison"]=="doh_warm" and r["baseline"]==baseline and r["metric"]=="elapsed_ms"]
                if found:
                    difference=values["doh_warm"]-values[baseline]
                    point[baseline+"_difference_of_marginal_medians_ms"]=difference
                    point[baseline+"_median_paired_delta_ms"]=found[0]["median_delta_ms"]
                    point[baseline+"_aggregation_gap_ms"]=difference-found[0]["median_delta_ms"]
            points.append(point)
        correlations=[]
        for baseline in ("udp_fresh","udp_bound"):
            x=np.asarray([p[baseline+"_centered_ms"] for p in points]);y=np.asarray([p["doh_warm_centered_ms"] for p in points])
            correlation=float(np.corrcoef(x,y)[0,1]) if len(x)>=3 and np.std(x)>0 and np.std(y)>0 else None
            correlations.append({"udp_baseline":baseline,"window_count":len(x),"pearson_centered_window_medians":correlation})
        marginal_ranges=[]
        for mode in ("doh_warm","udp_fresh","udp_bound"):
            values=[p[mode+"_median_ms"] for p in points]
            centered=[p[mode+"_centered_ms"] for p in points]
            per_session=[]
            for sid in sorted(set(p["session_id"] for p in points)):
                own=[p[mode+"_median_ms"] for p in points if p["session_id"]==sid]
                per_session.append({"session_id":sid,"window_count":len(own),"minimum_ms":min(own),"maximum_ms":max(own),"range_ms":max(own)-min(own)})
            if values:marginal_ranges.append({"protocol":mode,"window_count":len(values),"minimum_window_median_ms":min(values),"maximum_window_median_ms":max(values),
                                               "observed_window_median_range_ms":max(values)-min(values),"centered_minimum_ms":min(centered),"centered_maximum_ms":max(centered),
                                               "within_session_window_ranges":per_session})
        range_text="; ".join(f"{r['protocol']}: {r['minimum_window_median_ms']:.3f} to {r['maximum_window_median_ms']:.3f} ms (range {r['observed_window_median_range_ms']:.3f})" for r in marginal_ranges)
        out.append({"build_group":group,"session_count":len(set(p["session_id"] for p in points)),"window_points":points,"descriptive_correlations":correlations,"marginal_range_summary":marginal_ranges,
                    "reviewer_readout":f"Observed Google whole-call window marginal medians were {range_text}. These ranges show variation in measured client-and-service timings, but do not identify the responsible network path, cache, resolver, CPU or protocol stage. Per-session centered points and complete window values accompany this readout.",
                    "scope":"Exploratory marginal co-movement after centering each mode's window medians within session. Marginal medians retain all successful records for each treatment; paired contrasts require both matched treatments to succeed, so discordant failures can also change composition. No p-values, independence or causal/mechanism claim; repeated names and only a few selected windows remain."})
    return out


def write_csv(path,rows):
    if not rows:
        path.write_text("",encoding="utf-8")
        return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for r in rows:writer.writerow({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()})


def write_report(root,result):
    lines=["# Same-evening session extension results","",f"Analysis status: **{result['analysis_status']}**. Completed audited sessions: {result['chronology']['completed_sessions']}/{result['chronology']['planned_sessions']}.",
           "","All planned sessions remain in the status table. Running and missing sessions contribute no latency observations. Thresholds are sensitivity bands, not validated equivalence or utility bounds.","",
           "| Session | Scheduled start UTC | Actual start UTC | Status |","|---|---|---|---|"]
    for s in result["sessions"]:lines.append(f"| {s['session_id']} | {s['scheduled_start_utc']} | {s['actual_start_utc'] or 'Unavailable'} | {s['status']} |")
    completed=[s for s in result["sessions"] if s["status"]=="complete"]
    measured=sum(s["audit"]["measured_attempts"] for s in completed)
    primes=sum(s["audit"]["priming_records"] for s in completed)
    failed=sum(s["audit"]["failed_measured_attempts"] for s in completed)
    lines += ["",f"Audited complete sessions contain {measured:,} measured attempts and {primes:,} priming records. Measured failures: {failed}. Failed durations are never substituted for successful lookup latencies or threshold differences.",""]
    for session in completed:
        for failure in session["audit"]["failed_measurements"]:
            lines.append(f"- Retained failure: {session['session_id']}, {failure['provider']} / {failure['protocol']}, window {failure['window']}, {failure['domain']}: {failure['error']}.")
    lines += ["","## Established DoH minus pre-bound UDP","","| Session | Provider | Pairs | Signed paired median ms | Median absolute paired difference ms | Fraction of pairs outside ±2 ms |","|---|---|---:|---:|---:|---:|"]
    for e in result["session_effects"]:
        if e["comparison"]!="doh_warm" or e["baseline"]!="udp_bound" or e["metric"]!="elapsed_ms":continue
        rate=next(r for r in result["thresholds"]["paired_rates"] if r["level"]=="session" and r["session_id"]==e["session_id"] and r["provider"]==e["provider"] and r["comparison"]==e["comparison"] and r["baseline"]==e["baseline"] and r["metric"]==e["metric"] and r["threshold_ms"]==2)
        lines.append(f"| {e['session_id']} | {e['provider']} | {e['complete_pairs']} | {e['median_delta_ms']:+.3f} | {e['median_abs_delta_ms']:.3f} | {rate['fraction_abs_gt_threshold']:.3f} |")
    lines += ["","The signed paired median and the median absolute paired difference answer different questions. A signed median near zero can coexist with many individual paired differences exceeding a threshold. Pair rates do not equal rates of session/window medians.","","## Fixed Nov20 calibration forecasts","","The frozen point/sign/category forecasts were recorded before the new sessions. Historical data is not pooled into the new estimates. The source diff, full raw-input hash, source hashes and calibration snapshot are retained.",""]
    for p in result["prospective_summary"]:
        if p["baseline"]=="udp_bound" and p["session_count"]:
            lines.append(f"- {p['provider']}: fixed forecast {p['forecast_point_ms']:+.3f} ms; mean absolute session-median error {p['forecast_mae_ms']:.3f} ms versus {p['zero_adjustment_mae_ms']:.3f} ms for zero adjustment; sign matched {p['sign_matches']}/{p['session_count']} sessions.")
    lines += ["","## Exploratory Google marginal readout",""]
    for g in result["exploratory_google_covariation"]:lines.append(g["reviewer_readout"])
    lines += ["","## Dependence and interpretation","",result["interpretation"],"","Complete numerical threshold grids, window medians, treatment marginals, paired counts, prospective category scores and retrospective leave-session checks are in `results/session_extension/`. Retrospective leave-session results are never described as issued forecasts. Exploratory Google marginal correlations cannot locate a resolver, routing, cache or CPU mechanism.",""]
    (root/"docs/SESSION_EXTENSION_RESULTS.md").write_text("\n".join(lines),encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--require-complete",action="store_true")
    args=parser.parse_args();root=args.root.resolve();result=analyze(root)
    out=root/"results/session_extension";out.mkdir(parents=True,exist_ok=True)
    (out/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    for key in ("session_effects","window_effects","marginals","pairing_audits","prospective_forecasts","prospective_decisions","prospective_summary","leave_session_checks","leave_session_decisions","leave_session_summary"):
        write_csv(out/f"{key}.csv",result[key])
    write_csv(out/"session_statuses.csv",[{k:s.get(k) for k in ("session_id","directory","scheduled_start_utc","actual_start_utc","actual_finish_utc","status","build_group")} for s in result["sessions"]])
    for key in ("paired_rates","window_decisions","session_decisions"):write_csv(out/f"threshold_{key}.csv",result["thresholds"][key])
    write_report(root,result)
    print(json.dumps({"analysis_status":result["analysis_status"],"session_statuses":[{"session_id":s["session_id"],"status":s["status"]} for s in result["sessions"]],"effects":len(result["session_effects"]),"summary":"results/session_extension/summary.json"}))
    if args.require_complete and not result["chronology"]["is_final"]:raise SystemExit(1)


if __name__=="__main__":main()
