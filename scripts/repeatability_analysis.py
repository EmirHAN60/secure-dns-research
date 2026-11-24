"""Frozen, matched-position DNS A/A repeatability analysis; runs stay separate."""
from __future__ import annotations
import argparse
import base64
from collections import Counter,defaultdict
import csv
from datetime import datetime,timezone
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from analyze import decode_wire
from session_analysis import check_stages

PLAN="docs/REPEATABILITY_PLAN.json"
LOCK="docs/REPEATABILITY_SOURCE_LOCK.json"
ARCHIVE="docs/evidence/repeatability-source-2026-11-23"
CLASSES=("UU","DD","DU")


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def utc(value):return datetime.fromisoformat(value.replace("Z","+00:00"))
def median(values):
    values=list(values)
    return float(np.median(values)) if values else None
def read_json(path):return json.loads(path.read_text(encoding="utf-8-sig"))
def read_rows(path):return [json.loads(x) for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]


def verify_lock(root,plan):
    lock=read_json(root/LOCK)
    if lock["plan_sha256"]!=sha(root/PLAN):raise ValueError("Repeatability frozen plan hash mismatch")
    if lock["source_sha256"]!=plan["source_sha256"]:raise ValueError("Repeatability source lock mismatch")
    verified={}
    for name,digest in plan["source_sha256"].items():
        path=root/ARCHIVE/name
        if not path.exists():path=root/"scripts"/name
        if sha(path)!=digest:raise ValueError(f"Locked repeatability source mismatch: {name}")
        verified[name]={"sha256":digest,"verified_path":path.relative_to(root).as_posix()}
    return {"plan_sha256":sha(root/PLAN),"plan_recorded_utc":plan["recorded_utc"],"source_lock_sha256":sha(root/LOCK),
            "source_lock_recorded_utc":lock["recorded_utc"],"source_sha256":verified}


def audit(root,run,plan,env,rows,lock):
    d=plan["design"];errors=[];measured=[r for r in rows if r.get("phase")=="measure"];primes=[r for r in rows if r.get("phase")=="prime"]
    for field in ("windows","reps","interval_seconds","step_ms","seed"):
        if env.get(field)!=d[field]:errors.append(f"Frozen design mismatch {field}")
    if env.get("session_id")!=run["run_id"]:errors.append("Run identity mismatch")
    if env.get("source_sha256")!=plan["source_sha256"]:errors.append("Run source hashes differ from frozen sources")
    if env.get("analysis_plan_sha256")!=lock["plan_sha256"]:errors.append("Collector did not record frozen plan hash")
    if utc(env["started_utc"])<=max(utc(plan["recorded_utc"]),utc(lock["source_lock_recorded_utc"])):errors.append("Run precedes analysis plan/source lock")
    if len(measured)!=d["expected_measured_attempts_per_run"] or len(primes)!=d["expected_priming_attempts_per_run"]:errors.append("Attempt grid count mismatch")
    if len(rows)!=len(measured)+len(primes):errors.append("Unknown observation phase")
    if set(env.get("domains",[]))!=set(d["domains"]) or set(env.get("modes",[]))!=set(d["protocols"]) or set(env.get("flow_conditions",[]))!=set(d["flow_conditions"]):errors.append("Declared domain/mode/flow-condition mismatch")
    blocks=defaultdict(list);prime_grid=set();ids=set();wire_checks=0
    for r in rows:
        if r.get("provider") not in d["providers"] or r.get("domain") not in d["domains"] or r.get("protocol") not in d["protocols"] or r.get("window") not in range(1,d["windows"]+1) or r.get("flow_index") not in (0,1):
            errors.append("Record outside declared grid");continue
        if r.get("session_id")!=run["run_id"]:errors.append("Observation run identity mismatch")
        errors.extend(check_stages(r))
        if r["phase"]=="prime":
            key=tuple(r[k] for k in ("window","provider","domain","protocol","flow_index"))
            if key in prime_grid:errors.append("Duplicate primer")
            prime_grid.add(key)
        else:blocks[(r["window"],r["block_id"])].append(r)
        try:
            q=base64.b64decode(r["query_base64"],validate=True)
            identity=int.from_bytes(q[:2],"big")
            if identity in ids:errors.append("Repeated transaction ID within run")
            ids.add(identity)
            if r.get("valid") is True:
                if not decode_wire(r,r["domain"])["wire_valid"]:errors.append("Successful reply failed independent DNS semantics")
                wire_checks+=1
        except (KeyError,ValueError,TypeError) as e:errors.append(f"Wire validation: {e}")
        if r.get("valid") is not True:continue
        if r.get("remote_address")!=env["providers"][r["provider"]]["ip"]:errors.append("Requested provider destination mismatch")
        if not isinstance(r.get("local_port"),int) or not 0<r["local_port"]<65536:errors.append("Invalid local port")
        if r["protocol"]=="udp_bound":
            if r.get("remote_port")!=53 or r.get("bound_before_timing") is not True or r.get("udp_connected") is not False:errors.append("Ready UDP flags/port mismatch")
        elif r.get("remote_port")!=443 or r.get("alpn")!="h2" or r.get("connection_preexisting") is not True or r.get("tls_session_reused") is not False or r.get("http_status")!=200:errors.append("Established H2/TLS mismatch")
    if len(blocks)!=d["expected_blocks_per_run"]:errors.append("Four-attempt block count mismatch")
    cells=defaultdict(list);successful_blocks=0;schedule_hashes={}
    for (w,bid),block in blocks.items():
        block.sort(key=lambda r:r["position"])
        if len(block)!=4 or [r["position"] for r in block]!=[1,2,3,4]:errors.append("Incomplete four-position block");continue
        first=block[0]
        for field in ("provider","domain","flow_condition","sequence","first_udp_flow","first_doh_flow","rep","block_order","block_anchor_monotonic_ms"):
            if len({r[field] for r in block})!=1:errors.append(f"Inconsistent block field {field}")
        if first["sequence"] not in d["sequences"] or first["flow_condition"] not in d["flow_conditions"]:errors.append("Unexpected sequence/flow condition")
        letters="".join("U" if r["protocol"]=="udp_bound" else "D" for r in block)
        if letters!=first["sequence"]:errors.append("Observed mode order differs from sequence")
        cells[(w,first["provider"],first["domain"],first["flow_condition"])].append(first)
        seen=Counter()
        for index,r in enumerate(block):
            letter=letters[index];seen[letter]+=1
            initial=r["first_udp_flow"] if letter=="U" else r["first_doh_flow"]
            expected=1-initial if r["flow_condition"]=="distinct_flows" and seen[letter]==2 else initial
            if r["repeat_index"]!=seen[letter] or r["flow_index"]!=expected:errors.append("Within-mode repeat/flow assignment mismatch")
            planned=r["block_anchor_monotonic_ms"]+index*d["step_ms"]
            if not np.isclose(planned,r["planned_start_monotonic_ms"],atol=1e-6,rtol=0):errors.append("Planned start-slot arithmetic mismatch")
            if not np.isclose(r["actual_start_monotonic_ms"],r["query_start_monotonic_ms"],atol=1e-6,rtol=0):errors.append("Internal/actual measured start mismatch")
            if not np.isclose(r["measurement_end_monotonic_ms"],r["actual_start_monotonic_ms"]+r["elapsed_ms"],atol=1e-6,rtol=0):errors.append("End/elapsed arithmetic mismatch")
            if not np.isclose(r["start_lateness_ms"],r["actual_start_monotonic_ms"]-planned,atol=1e-6,rtol=0):errors.append("Lateness arithmetic mismatch")
            if index and r["actual_start_monotonic_ms"]+1e-6<block[index-1]["measurement_end_monotonic_ms"]:errors.append("Measured calls overlap despite awaited design")
        successful_blocks+=all(r.get("valid") is True for r in block)
    if len(cells)!=d["windows"]*2*len(d["domains"])*2:errors.append("Provider/domain/window/condition grid mismatch")
    for cell in cells.values():
        if Counter(r["sequence"] for r in cell)!=Counter({x:1 for x in d["sequences"]}):errors.append("Six-order balance mismatch")
        for field in ("first_udp_flow","first_doh_flow"):
            if Counter(r[field] for r in cell)!=Counter({0:3,1:3}):errors.append("First-flow3/3 balance mismatch")
    for w in range(1,d["windows"]+1):
        schedule=root/run["directory"]/f"schedule-window-{w}.json"
        if not schedule.exists():errors.append("Missing stored block schedule");continue
        pool=read_json(schedule);schedule_hashes[str(w)]=sha(schedule)
        if len(pool)!=240:errors.append("Stored schedule length mismatch")
        for (window,_),block in blocks.items():
            if window!=w:continue
            first=block[0];position=first["block_order"]-1
            if not 0<=position<len(pool):errors.append("Block order outside schedule");continue
            for key,value in pool[position].items():
                if any(r.get(key)!=value for r in block):errors.append("Observed block differs from stored randomized schedule")
    flow_groups=[]
    for w in range(1,d["windows"]+1):
        for provider in d["providers"]:
            for protocol in d["protocols"]:
                ports=[]
                for f in (0,1):
                    own=[r for r in rows if r["window"]==w and r["provider"]==provider and r["protocol"]==protocol and r["flow_index"]==f]
                    valid=[r for r in own if r.get("valid") is True]
                    measured_own=[r for r in own if r["phase"]=="measure"]
                    if len(measured_own)!=120:errors.append("Prepared-flow workload differs from120 measured attempts")
                    identities={r["flow_id"] for r in own};local={r.get("local_port") for r in valid}
                    if len(identities)!=1:errors.append("Flow identity changed")
                    if valid and len(local)!=1:errors.append("Persistent flow port changed")
                    if local:ports.extend(local)
                    counters=[r.get("connection_query_number") for r in valid]
                    if counters!=sorted(set(counters)):errors.append("Persistent query numbers not strictly increasing")
                    if protocol=="doh_warm" and valid:
                        fingerprints={(r.get("connection_id"),r.get("connect_ms"),r.get("tls_version"),r.get("alpn"),r.get("remote_address")) for r in valid}
                        if len(fingerprints)!=1:errors.append("Persistent H2 metadata changed")
                    flow_groups.append({"window":w,"provider":provider,"protocol":protocol,"flow_index":f,"flow_id":next(iter(identities),None),"successful_records":len(valid),"measured_attempts":len(measured_own),"distinct_local_port_count":len(local)})
                if len(ports)!=len(set(ports)):errors.append("The two prepared same-protocol flows share a local port")
    return {"errors":sorted(set(errors)),"raw_records":len(rows),"measured_attempts":len(measured),"priming_attempts":len(primes),
            "successful_measured_attempts":sum(r.get("valid") is True for r in measured),"failed_measured_attempts":sum(r.get("valid") is not True for r in measured),
            "measured_blocks":len(blocks),"fully_successful_blocks":successful_blocks,"independent_wire_checks":wire_checks,
            "failures":[{k:r.get(k) for k in ("window","provider","domain","protocol","flow_condition","block_id","position","elapsed_ms","error")} for r in measured if r.get("valid") is not True],
            "raw_sha256":sha(root/run["directory"]/"repeatability_raw.jsonl"),"source_sha256":env["source_sha256"],
            "plan_and_lock_precede_start":utc(env["started_utc"])>max(utc(plan["recorded_utc"]),utc(lock["source_lock_recorded_utc"])),
            "schedule_hashes":schedule_hashes,"unique_schedule_hash_count":len(set(schedule_hashes.values())),"flow_groups":flow_groups}


def pair_observations(rows,run_id):
    blocks=defaultdict(list)
    for r in rows:
        if r["phase"]=="measure":blocks[(r["window"],r["block_id"])].append(r)
    pairs=[]
    for (window,bid),block in sorted(blocks.items()):
        block.sort(key=lambda r:r["position"])
        for a,b in itertools.combinations(block,2):
            amode="U" if a["protocol"]=="udp_bound" else "D";bmode="U" if b["protocol"]=="udp_bound" else "D"
            cls=amode+bmode if amode==bmode else "DU";valid=a.get("valid") is True and b.get("valid") is True
            lag=b["actual_start_monotonic_ms"]-a["actual_start_monotonic_ms"]
            delta=None
            if valid:
                delta=b["elapsed_ms"]-a["elapsed_ms"]
                if amode!=bmode and amode=="D":delta=-delta
            pairs.append({"run_id":run_id,"provider":a["provider"],"flow_condition":a["flow_condition"],"window":window,"domain":a["domain"],"block_id":bid,
                          "sequence":a["sequence"],"position_pair":f"{a['position']}-{b['position']}","position_separation":b["position"]-a["position"],"pair_class":cls,
                          "chronological_mode_order":amode+bmode,"actual_start_lag_ms":lag,"idle_after_first_completion_ms":b["actual_start_monotonic_ms"]-a["measurement_end_monotonic_ms"],
                          "pair_valid":valid,"signed_delta_ms":delta,"abs_delta_ms":abs(delta) if delta is not None else None,
                          "first_flow_id":a["flow_id"],"second_flow_id":b["flow_id"],"first_flow_index":a["flow_index"],"second_flow_index":b["flow_index"],
                          "first_start_lateness_ms":a["start_lateness_ms"],"second_start_lateness_ms":b["start_lateness_ms"],
                          "primary_lag_eligible":valid and b["position"]-a["position"]==1 and 75<=lag<=125,
                          "pair_failure_reason":None if valid else " | ".join(r.get("error") or "Invalid response" for r in (a,b) if r.get("valid") is not True)})
    return pairs


def eligible(pair,spec,step):
    if not pair["pair_valid"]:return False
    if "positions" in spec and pair["position_pair"] not in spec["positions"]:return False
    if "position_separation" in spec and pair["position_separation"]!=spec["position_separation"]:return False
    band=spec.get("lag_ms_inclusive")
    if band and not band[0]<=pair["actual_start_lag_ms"]<=band[1]:return False
    relative=spec.get("relative_target_lag_inclusive")
    if relative:
        ratio=pair["actual_start_lag_ms"]/(step*pair["position_separation"])
        if not relative[0]<=ratio<=relative[1]:return False
    return True


def weighted_quantile(observations,value,q):
    target=Fraction(q)*sum((w for _,w in observations),Fraction(0))
    accumulated=Fraction(0)
    for row,weight in sorted(observations,key=lambda x:x[0][value]):
        accumulated+=weight
        if accumulated>=target:return float(row[value])
    return None


def common_estimates(pairs,plan,spec,run_id,provider,condition,view_name,windows=None):
    windows=windows or list(range(1,plan["design"]["windows"]+1));own=[p for p in pairs if p["provider"]==provider and p["flow_condition"]==condition and p["window"] in windows]
    cells=defaultdict(lambda:defaultdict(list))
    for p in own:
        if eligible(p,spec,plan["design"]["step_ms"]):cells[(p["window"],p["domain"],p["position_pair"])][p["pair_class"]].append(p)
    common={k:v for k,v in cells.items() if all(c in v for c in CLASSES)}
    per_window={w:sum(k[0]==w for k in common) for w in windows}
    positions=spec.get("positions") or [f"{i}-{i+spec['position_separation']}" for i in range(1,5-spec["position_separation"])]
    planned_cells=len(windows)*len(plan["design"]["domains"])*len(positions)
    available=all(per_window.values())
    meta={"run_id":run_id,"provider":provider,"flow_condition":condition,"view":view_name,"common_cells":len(common),"planned_cells":planned_cells,
          "common_cells_by_window":{str(k):v for k,v in per_window.items()},"estimate_status":"available" if available else "insufficient_common_lag_overlap"}
    classes=[];rates=[]
    for cls in CLASSES:
        observations=[]
        for key,cell in common.items():
            if available:
                denominator=len(windows)*per_window[key[0]]*len(cell[cls])
                observations.extend((row,Fraction(1,denominator)) for row in cell[cls])
        base={**meta,"pair_class":cls,"pair_count":len(observations),"distinct_blocks":len({(r['window'],r['block_id']) for r,_ in observations})}
        if observations:
            total=sum((w for _,w in observations),Fraction(0))
            if total!=1:raise ValueError("Exact conditional pair weights do not sum to one")
            base.update(weighted_median_abs_delta_ms=weighted_quantile(observations,"abs_delta_ms",Fraction(1,2)),
                        weighted_median_signed_delta_ms=weighted_quantile(observations,"signed_delta_ms",Fraction(1,2)),
                        weighted_q25_abs_delta_ms=weighted_quantile(observations,"abs_delta_ms",Fraction(1,4)),weighted_q75_abs_delta_ms=weighted_quantile(observations,"abs_delta_ms",Fraction(3,4)),
                        weighted_median_actual_lag_ms=weighted_quantile(observations,"actual_start_lag_ms",Fraction(1,2)),
                        minimum_actual_lag_ms=min(r["actual_start_lag_ms"] for r,_ in observations),maximum_actual_lag_ms=max(r["actual_start_lag_ms"] for r,_ in observations))
            for t in plan["thresholds_ms"]:
                fraction=sum((w for r,w in observations if r["abs_delta_ms"]>t),Fraction(0))
                rates.append({**meta,"pair_class":cls,"threshold_ms":t,"pair_count":len(observations),"weighted_fraction_abs_gt_threshold":float(fraction)})
        else:
            for name in ("weighted_median_abs_delta_ms","weighted_median_signed_delta_ms","weighted_q25_abs_delta_ms","weighted_q75_abs_delta_ms","weighted_median_actual_lag_ms","minimum_actual_lag_ms","maximum_actual_lag_ms"):base[name]=None
        classes.append(base)
    cell_details=[]
    for w in windows:
        for domain in plan["design"]["domains"]:
            for position in positions:
                key=(w,domain,position)
                detail={"window":w,"domain":domain,"position_pair":position,"common_cell":key in common}
                for cls in CLASSES:
                    candidate=[p for p in own if p["window"]==w and p["domain"]==domain and p["position_pair"]==position and p["pair_class"]==cls]
                    detail[cls.lower()+"_candidate_pairs"]=len(candidate)
                    detail[cls.lower()+"_successful_pairs"]=sum(p["pair_valid"] for p in candidate)
                    detail[cls.lower()+"_lag_eligible_pairs"]=sum(eligible(p,spec,plan["design"]["step_ms"]) for p in candidate)
                cell_details.append(detail)
    return classes,rates,{**meta,"cell_eligibility":cell_details,"excluded_cells":[x for x in cell_details if not x["common_cell"]]}


def summaries(pairs,plan,run_id):
    primary=[];thresholds=[];comparisons=[];window_primary=[];sensitivities=[];sensitivity_rates=[];overlap=[]
    spec=plan["primary"]
    for provider in plan["design"]["providers"]:
        for condition in plan["design"]["flow_conditions"]:
            classes,rates,meta=common_estimates(pairs,plan,spec,run_id,provider,condition,"primary_adjacent_75_125ms")
            primary.extend(classes);overlap.append(meta)
            meta={k:v for k,v in meta.items() if k not in ("cell_eligibility","excluded_cells")}
            if meta["estimate_status"]=="available":
                lookup={r["pair_class"]:r for r in classes};du=lookup["DU"]
                comparisons.append({**meta,"du_median_abs_delta_ms":du["weighted_median_abs_delta_ms"],"uu_median_abs_delta_ms":lookup["UU"]["weighted_median_abs_delta_ms"],"dd_median_abs_delta_ms":lookup["DD"]["weighted_median_abs_delta_ms"],
                                    "difference_in_abs_medians_du_minus_uu_ms":du["weighted_median_abs_delta_ms"]-lookup["UU"]["weighted_median_abs_delta_ms"],
                                    "difference_in_abs_medians_du_minus_dd_ms":du["weighted_median_abs_delta_ms"]-lookup["DD"]["weighted_median_abs_delta_ms"]})
                for t in plan["thresholds_ms"]:
                    byclass={r["pair_class"]:r for r in rates if r["threshold_ms"]==t}
                    row={**meta,"threshold_ms":t}
                    for cls,prefix in (("UU","uu"),("DD","dd"),("DU","du")):
                        row[prefix+"_fraction_abs_gt_threshold"]=byclass[cls]["weighted_fraction_abs_gt_threshold"]
                        row[prefix+"_pair_count"]=byclass[cls]["pair_count"]
                    thresholds.append(row)
            for w in range(1,plan["design"]["windows"]+1):
                cs,_,_=common_estimates(pairs,plan,spec,run_id,provider,condition,"primary_window",[w])
                window_primary.extend({**c,"window":w} for c in cs)
            for sensitivity in plan["sensitivity"]:
                cs,rs,_=common_estimates(pairs,plan,sensitivity,run_id,provider,condition,sensitivity["name"])
                sensitivities.extend(cs)
                sensitivity_rates.extend(rs)
    strata=defaultdict(list)
    for p in pairs:
        relative_lag=p["actual_start_lag_ms"]/(plan["design"]["step_ms"]*p["position_separation"])
        band="on_target" if .75<=relative_lag<=1.25 else "short_lag" if relative_lag<.75 else "long_lag"
        strata[(p["provider"],p["flow_condition"],p["window"],p["position_pair"],p["pair_class"],p["chronological_mode_order"],band)].append(p)
    stratum_rows=[]
    for key,values in sorted(strata.items()):
        valid=[p for p in values if p["pair_valid"]]
        stratum_rows.append(dict(zip(("provider","flow_condition","window","position_pair","pair_class","chronological_mode_order","lag_band"),key))|
                            {"run_id":run_id,"candidate_pairs":len(values),"successful_pairs":len(valid),"failed_pairs":len(values)-len(valid),
                             "median_abs_delta_ms":median(p["abs_delta_ms"] for p in valid),"median_signed_delta_ms":median(p["signed_delta_ms"] for p in valid),
                             "median_actual_start_lag_ms":median(p["actual_start_lag_ms"] for p in values),"q25_actual_start_lag_ms":float(np.quantile([p["actual_start_lag_ms"] for p in values],.25)),
                             "q75_actual_start_lag_ms":float(np.quantile([p["actual_start_lag_ms"] for p in values],.75)),"minimum_lag_ms":min(p["actual_start_lag_ms"] for p in values),"maximum_lag_ms":max(p["actual_start_lag_ms"] for p in values)})
    return {"primary_classes":primary,"primary_magnitude_comparisons":comparisons,"threshold_comparisons":thresholds,"window_primary_classes":window_primary,"sensitivity_classes":sensitivities,"sensitivity_threshold_rates":sensitivity_rates,
            "common_overlap":overlap,"position_lag_strata":stratum_rows,"candidate_pair_count":len(pairs),"successful_pair_count":sum(p["pair_valid"] for p in pairs),
            "primary_lag_eligible_pair_count":sum(p["primary_lag_eligible"] for p in pairs)}


def csv_write(path,rows):
    if not rows:path.write_text("",encoding="utf-8");return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in rows:writer.writerow({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()})


def timing_diagnostics(rows,run_id):
    """Ordinary empirical timing summaries of every attempted measured call."""
    groups=defaultdict(list)
    for r in rows:
        if r["phase"]=="measure":groups[(r["provider"],r["flow_condition"],r["window"],r["protocol"])].append(r)
    result=[]
    for key,own in sorted(groups.items()):
        out=dict(zip(("provider","flow_condition","window","protocol"),key))
        out.update(run_id=run_id,attempt_count=len(own),failed_attempt_count=sum(r.get("valid") is not True for r in own),
                   quantile_definition="Ordinary empirical linear-interpolated quantiles; descriptive diagnostics, separate from weighted inverse-CDF primary summaries")
        for field in ("elapsed_ms","start_lateness_ms"):
            values=[r[field] for r in own]
            for name,value in zip(("minimum","q25","median","q75","maximum"),np.quantile(values,[0,.25,.5,.75,1])):
                out[f"{field}_{name}"]=float(value)
        result.append(out)
    return result


def run_analysis(root,run,plan,lock):
    status={**run,"status":"not_collected","summary_path":f"results/repeatability/{run['run_id']}/summary.json","audit":None}
    directory=root/run["directory"]
    if not (directory/"environment.json").exists():return status,None,None
    env=read_json(directory/"environment.json");status.update(actual_start_utc=env.get("started_utc"),actual_finish_utc=env.get("finished_utc"))
    if env.get("status")!="complete":
        status["status"]="running" if env.get("status")=="running" else "collection_not_complete"
        return status,None,None
    try:
        rows=read_rows(directory/"repeatability_raw.jsonl");checked=audit(root,run,plan,env,rows,lock);status["audit"]=checked
        if checked["errors"]:status["status"]="invalid";return status,None,None
        pairs=pair_observations(rows,run["run_id"]);result=summaries(pairs,plan,run["run_id"])
        result["timing_diagnostics"]=timing_diagnostics(rows,run["run_id"])
    except (ValueError,KeyError,TypeError,OSError) as e:
        status.update(status="invalid",error=str(e));return status,None,None
    status["status"]="complete"
    result.update(run_id=run["run_id"],context_label=run["context_label"],audit=checked,actual_start_utc=env["started_utc"],actual_finish_utc=env.get("finished_utc"),
                  interpretation=plan["interpretation"],weighting=plan["primary"]["weighting"],quantile_definition=plan["primary"]["quantile"])
    return status,result,pairs


def write_report(root,result):
    lines=["# Remote same-mode repeatability controls","","Each run remains separate. Weighted primary summaries compare successful adjacent-position pairs with observed start lag75–125ms in common cells. Windows, common cells within windows and eligible observations within class/cell receive equal respective weight. These are descriptive empirical distributions, not independent-pair population estimates.","","| Run | Status | Measured attempts | Failures | Fully successful blocks |","|---|---|---:|---:|---:|"]
    for r in result["runs"]:
        a=r["audit"] or {}
        lines.append(f"| {r['run_id']} | {r['status']} | {a.get('measured_attempts','Unavailable')} | {a.get('failed_measured_attempts','Unavailable')} | {a.get('fully_successful_blocks','Unavailable')} |")
    lines += ["","## Repeat-flow illustration at 2 ms","","| Run | Provider | Common cells | Median abs. UU (ms) | Median abs. DD (ms) | Median abs. DU (ms) | UU >2ms | DD >2ms | DU >2ms |","|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in result["threshold_comparisons"]:
        if r["flow_condition"]!="repeat_flow" or r["threshold_ms"]!=2:continue
        classes={c["pair_class"]:c for c in result["primary_classes"] if all(c[k]==r[k] for k in ("run_id","provider","flow_condition"))}
        lines.append(f"| {r['run_id']} | {r['provider']} | {r['common_cells']} | {classes['UU']['weighted_median_abs_delta_ms']:.3f} | {classes['DD']['weighted_median_abs_delta_ms']:.3f} | {classes['DU']['weighted_median_abs_delta_ms']:.3f} | {r['uu_fraction_abs_gt_threshold']:.1%} | {r['dd_fraction_abs_gt_threshold']:.1%} | {r['du_fraction_abs_gt_threshold']:.1%} |")
    lines += ["","All percentages above use the frozen conditional weights; they need not equal an integer count divided by the pooled pair count when common-cell counts differ across windows. Primary lag/overlap exclusions are retained in each run's common_overlap.csv and summary.json, with all-lag sensitivity alongside the conditional primary analysis.","","UU/DD are same-mode repeats; DU is DoH-minus-UDP before taking magnitude. All four thresholds and both flow conditions remain in the numerical outputs. Cross-mode magnitude is not corrected by subtracting a same-mode jitter median. Pair observations share blocks/attempts and are dependent.","","## Scope and availability","",result["interpretation"],"","A1/B1/A2 denote planned user-confirmed contexts. A-B-A is described only when all three runs are actually collected. Fixed network order and elapsed time prevent a causal network-effect claim. No raw network names or secrets are required. Running and missing runs supply no inspected outcome data.",""]
    (root/"docs/REPEATABILITY_RESULTS.md").write_text("\n".join(lines),encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument("--require-runs",default="")
    args=parser.parse_args();root=args.root.resolve();plan=read_json(root/PLAN);lock=verify_lock(root,plan)
    result={"generated_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"schema_version":1,"plan_validation":lock,"runs":[],"primary_classes":[],"primary_magnitude_comparisons":[],"threshold_comparisons":[],"interpretation":plan["interpretation"]}
    out=root/"results/repeatability";out.mkdir(parents=True,exist_ok=True)
    for run in plan["runs"]:
        status,summary,pairs=run_analysis(root,run,plan,lock);result["runs"].append(status)
        if summary is None:continue
        own=out/run["run_id"];own.mkdir(exist_ok=True)
        (own/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
        csv_write(own/"pair_observations.csv",pairs)
        for key in ("primary_classes","primary_magnitude_comparisons","threshold_comparisons","window_primary_classes","sensitivity_classes","sensitivity_threshold_rates","common_overlap","position_lag_strata","timing_diagnostics"):
            csv_write(own/f"{key}.csv",summary[key])
        for key in ("primary_classes","primary_magnitude_comparisons","threshold_comparisons"):result[key].extend(summary[key])
    schedules=[{"run_id":r["run_id"],"window":w,"sha256":h} for r in result["runs"] if r["status"]=="complete" for w,h in r["audit"]["schedule_hashes"].items()]
    hashes=Counter(r["sha256"] for r in schedules)
    result["schedule_distinctness"]={"observed_schedule_count":len(schedules),"unique_schedule_hash_count":len(hashes),"duplicate_hashes":[h for h,n in hashes.items() if n>1],"schedules":schedules}
    result["completed_run_ids"]=[r["run_id"] for r in result["runs"] if r["status"]=="complete"]
    result["all_three_run_ids_collected"]=result["completed_run_ids"]==["A1","B1","A2"]
    result["available_data_scope"]="Separate completed runs only; no cross-run pooling. Context labels alone do not identify a physical route."
    (out/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    for key in ("primary_classes","primary_magnitude_comparisons","threshold_comparisons"):csv_write(out/f"{key}.csv",result[key])
    write_report(root,result)
    print(json.dumps({"runs":[{"run_id":r["run_id"],"status":r["status"]} for r in result["runs"]],"primary_classes":len(result["primary_classes"])}))
    required=[x for x in args.require_runs.split(",") if x]
    if any(x not in result["completed_run_ids"] for x in required):raise SystemExit(1)


if __name__=="__main__":main()
