"""Offline analysis of actual browser observations under synthetic delay gates."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from pathlib import Path

SEED=20261122
RESAMPLES=4000

def median(a):
    return statistics.median(a) if a else None

def quantile(a,p):
    if not a: return None
    s=sorted(a); k=(len(s)-1)*p; lo=math.floor(k); hi=math.ceil(k)
    return s[lo]+(k-lo)*(s[hi]-s[lo])

def describe(a):
    return {'n':len(a),'median_ms':median(a),'q1_ms':quantile(a,.25),'q3_ms':quantile(a,.75),'min_ms':min(a) if a else None,'max_ms':max(a) if a else None}

def ci(a,label):
    if not a: return [None,None]
    rng=random.Random(SEED^int.from_bytes(hashlib.sha256(label.encode()).digest()[:8],'big'))
    samples=[statistics.median(rng.choices(a,k=len(a))) for _ in range(RESAMPLES)]
    return [quantile(samples,.025),quantile(samples,.975)]

def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        if not rows: return
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def independent_audit(row,design):
    errors=[]; gates=row.get('gates',[]); fixture=row.get('fixture',{})
    if row.get('status')!='ok': errors.append('collector status is not ok')
    if len(gates)!=7 or {g.get('index') for g in gates}!={1,2,3,4,5,6,7}: errors.append('expected seven distinct indexed gates')
    if len({g.get('hostname') for g in gates})!=7: errors.append('expected seven distinct hostnames')
    if row.get('unexpected_requests'): errors.append('unexpected context network request')
    if row.get('errors') or fixture.get('error'): errors.append('collector or fixture error')
    if fixture.get('loaded_images')!=7: errors.append('not all images loaded')
    if row.get('html_sha256')!=design['html_sha256'] or row.get('image_sha256')!=design['image_sha256']: errors.append('payload hash mismatch')
    active=0;maximum=0;events=[]
    for g in gates:
        if g.get('release_ms') is None or g['release_ms']<g['start_ms']: errors.append('invalid gate interval');continue
        events.extend([(g['start_ms'],1),(g['release_ms'],-1)])
        actual=g['release_ms']-g['start_ms']
        if abs(actual-g.get('actual_wait_ms',-1))>1e-7: errors.append('gate duration mismatch')
        if g.get('requested_delay_ms')!=row['requested_gate_ms']: errors.append('wrong delay treatment')
    for _,delta in sorted(events,key=lambda x:(x[0],x[1])):
        active+=delta;maximum=max(maximum,active)
    if maximum!=row.get('max_concurrent_gates'): errors.append('collector concurrency mismatch')
    req=fixture.get('requests',[])
    if len(req)!=7 or {r.get('index') for r in req}!={1,2,3,4,5,6,7}: errors.append('expected seven browser requests')
    if any(r.get('completed_ms') is None or not r.get('loaded') for r in req): errors.append('request completion missing')
    if not errors:
        if row['layout']=='sequential':
            if maximum!=1 or any(req[i]['requested_ms']<req[i-1]['completed_ms'] for i in range(1,7)): errors.append('sequential dependency violated')
        else:
            if maximum<2 or max(r['requested_ms'] for r in req)>min(r['completed_ms'] for r in req): errors.append('parallel dependency violated')
        elapsed=fixture['completed_ms']-fixture['start_ms']
        if abs(elapsed-fixture['elapsed_ms'])>1e-7: errors.append('fixture interval arithmetic mismatch')
    return {'id':row['id'],'rep':row['rep'],'layout':row['layout'],'extra_ms':row['extra'],'max_concurrent_gates':maximum,'median_actual_gate_wait_ms':median([g['actual_wait_ms'] for g in gates if 'actual_wait_ms' in g]),'valid':not errors,'errors':'; '.join(errors)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,default=Path('data/browser-layout-2026-11-22'))
    p.add_argument('--out',type=Path,default=Path('results/browser-layout-2026-11-22'))
    p.add_argument('--doc',type=Path)
    args=p.parse_args()
    design=json.loads((args.data/'design.json').read_text(encoding='utf-8'))
    environment=json.loads((args.data/'environment.json').read_text(encoding='utf-8'))
    completion=json.loads((args.data/'completion.json').read_text(encoding='utf-8'))
    schedule=json.loads((args.data/'schedule.json').read_text(encoding='utf-8'))
    rows=[json.loads(x) for x in (args.data/'pages.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    if len({r['id'] for r in rows})!=len(rows): raise ValueError('Duplicate page ids')
    if completion['status']!='complete' or completion['attempted']!=len(rows) or len(rows)!=design['repetitions']*4: raise ValueError('Incomplete collection')
    for name,key in [('fixture.html','html_sha256'),('fixture.svg','image_sha256')]:
        if hashlib.sha256((args.data/name).read_bytes()).hexdigest()!=design[key]: raise ValueError('Saved fixture bytes differ from design')
    for name,key in [('collector_snapshot.mjs','collector_sha256'),('analyzer_snapshot.py','analyzer_sha256')]:
        if hashlib.sha256((args.data/name).read_bytes()).hexdigest()!=design[key]: raise ValueError('Execution source snapshot differs from design')
    # Independently regenerate the declared JS LCG shuffle and compare every
    # scheduled condition, followed by every raw observation in execution order.
    state=design['seed']&0xffffffff
    def shuffle(a):
        nonlocal state
        a=list(a)
        for i in range(len(a)-1,0,-1):
            state=(1664525*state+1013904223)&0xffffffff
            j=math.floor((state/4294967296)*(i+1))
            a[i],a[j]=a[j],a[i]
        return a
    expected=[]
    for rep in shuffle(range(1,design['repetitions']+1)):
        for condition in shuffle(design['conditions']): expected.append({'rep':rep,**condition})
    if schedule!=expected or len(rows)!=len(schedule): raise ValueError('Frozen schedule differs from seeded design or collection count')
    for i,(row,scheduled) in enumerate(zip(rows,schedule),1):
        if row.get('order')!=i or any(row.get(k)!=v for k,v in scheduled.items()): raise ValueError(f'Raw observation {i} differs from frozen schedule')
    audits=[independent_audit(r,design) for r in rows]
    accepted={a['id'] for a in audits if a['valid']}
    summaries=[];effects=[];pairs=[];layout_deltas={}
    added=next(c['extra'] for c in design['conditions'] if c['extra']>0)
    for layout in ['parallel','sequential']:
        for extra in [0,added]:
            group=[r for r in rows if r['layout']==layout and r['extra']==extra]
            good=[r for r in group if r['id'] in accepted]
            summaries.append({'layout':layout,'extra_ms':extra,'requested_gate_ms':group[0]['requested_gate_ms'],'attempted':len(group),'succeeded':len(good),'failed':len(group)-len(good),**describe([r['fixture']['elapsed_ms'] for r in good]),'median_navigation_completion_ms':median([r['fixture']['completed_ms'] for r in good]),'median_load_event_end_ms':median([r.get('navigation',{}).get('loadEventEnd',0) for r in good]),'min_concurrent_gates':min(r['max_concurrent_gates'] for r in good) if good else None,'max_concurrent_gates':max(r['max_concurrent_gates'] for r in good) if good else None})
        by_rep={}
        for r in rows:
            if r['layout']==layout: by_rep.setdefault(r['rep'],{})[r['extra']]=r
        deltas={}
        for rep,modes in sorted(by_rep.items()):
            b,t=modes.get(0),modes.get(added)
            if not b or not t or b['id'] not in accepted or t['id'] not in accepted: continue
            delta=t['fixture']['elapsed_ms']-b['fixture']['elapsed_ms']
            deltas[rep]=delta
            pairs.append({'rep':rep,'layout':layout,'baseline_ms':b['fixture']['elapsed_ms'],'treatment_ms':t['fixture']['elapsed_ms'],'delta_ms':delta,'navigation_delta_ms':t['fixture']['completed_ms']-b['fixture']['completed_ms']})
        layout_deltas[layout]=deltas
        low,high=ci(list(deltas.values()),layout)
        effects.append({'layout':layout,'complete_pairs':len(deltas),'median_paired_delta_ms':median(list(deltas.values())),'ci95_low_ms':low,'ci95_high_ms':high,'idealized_delay_only_increment_ms':added*(7 if layout=='sequential' else 1)})
    interaction=[layout_deltas['sequential'][rep]-layout_deltas['parallel'][rep] for rep in sorted(set(layout_deltas['parallel'])&set(layout_deltas['sequential']))]
    low,high=ci(interaction,'interaction')
    summary={'study_type':'Real Chrome observations of synthetic delay-injection treatments; no live DNS or public content transfer','design':design,'environment':environment,'completion':completion,'counts':{'attempted':len(rows),'valid':len(accepted),'invalid':len(rows)-len(accepted)},'marginal_summary':summaries,'paired_effects':effects,'interaction':{'definition':'Per-repetition (sequential treatment-minus-baseline) minus (parallel treatment-minus-baseline), aggregated by median','complete_blocks':len(interaction),'median_ms':median(interaction),'ci95_low_ms':low,'ci95_high_ms':high},'validation':{'errors':[a for a in audits if not a['valid']],'checks':'Independent gate interval/concurrency recomputation, browser request sequencing, seven image completions, payload hashes, no unexpected context requests, full scheduled collection'},'inference':{'primary_metric':'Browser script start to verified completion of all seven fixed images','bootstrap':'4000 percentile resamples of paired repetition blocks, fixed seed 20261122, conditional on this local run; no population or native-browser-DNS coverage claim','timing':'Actual requested/released gate times are retained. Nominal injected durations are treatments, not assumed perfectly exact elapsed waits. Navigation loadEventEnd is diagnostic and can differ from application completion.'}}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    for name,data in [('marginal_summary.csv',summaries),('paired_effects.csv',effects),('paired_observations.csv',pairs),('gate_audit.csv',audits)]: write_csv(args.out/name,data)
    if args.doc:
        text=['# Controlled browser delay and layout experiment','','This is a separate causal delay-injection experiment in real headless Chrome. Its gate durations are synthetic treatments. It does not measure DNS, native browser resolution or Internet website loading.','','## Design','',f"The same HTML and seven identical SVG payloads were used throughout. Seven distinct fixture hostnames were fulfilled by Playwright routing. Main-document delivery had no added delay. Resource gates requested {design['conditions'][0]['requested_gate_ms']:.0f} ms at baseline and {design['conditions'][0]['requested_gate_ms']+added:.0f} ms in treatment. Each randomized repetition block included both delays under sequential and parallel image scheduling. The completed run contains {len(rows)} navigations ({design['repetitions']} per condition).",'',"Sequential JavaScript awaited each image's load before assigning the next image URL. Parallel JavaScript assigned all seven URLs before awaiting their joint completion. Actual gate intervals and browser request/completion timestamps verify these dependencies. The primary outcome is the interval from fixture script start to all seven verified image completions. Navigation Timing load-event end is retained only as a diagnostic.",'','## Measured paired effects','','| Layout | Complete pairs | Median treatment − baseline ms | Conditional 95% interval ms | Delay-only model increment ms |','| --- | ---: | ---: | --- | ---: |']
        for e in effects: text.append(f"| {e['layout']} | {e['complete_pairs']} | {e['median_paired_delta_ms']:+.2f} | [{e['ci95_low_ms']:+.2f}, {e['ci95_high_ms']:+.2f}] | {e['idealized_delay_only_increment_ms']:.0f} |")
        text+=['',f"The median paired interaction (sequential increment minus parallel increment within a repetition) was {median(interaction):+.2f} ms, with a conditional interval of [{low:+.2f}, {high:+.2f}] ms. The model column is an idealized prediction from the assigned delay and dependency graph; it is not a measured DNS result.",'','## Validation and interpretation','',f"Independent checks accepted {len(accepted)}/{len(rows)} records. They verified fixed payload hashes, distinct gates, successful image completion, browser sequence ordering and recomputed concurrent gate counts. Unexpected context requests were aborted and logged. Wildcard host resolution was disabled for the browser. The collector contacted no public DNS resolver or content host.",'',"The experiment tests whether the resource dependency graph changes how an injected wait accumulates. It does not estimate encryption cost, native resolver policy or user-perceived performance on arbitrary websites. Paired bootstrap intervals condition on this host, run, fixture and timing treatments. Browser/runtime scheduling and route fulfillment remain part of the measured interval.",'',"Raw files are in the matching data/browser-layout directory; the analysis produces summary.json, marginal_summary.csv, paired_effects.csv, paired_observations.csv and gate_audit.csv. The design, schedule, environment, constant payload bytes and screenshots accompany the recorded observations.",'']
        args.doc.parent.mkdir(parents=True,exist_ok=True);args.doc.write_text('\n'.join(text),encoding='utf-8')
    print(json.dumps({'counts':summary['counts'],'effects':effects,'interaction':summary['interaction']},indent=2))
    if len(accepted)!=len(rows): raise SystemExit(2)

if __name__=='__main__': main()
