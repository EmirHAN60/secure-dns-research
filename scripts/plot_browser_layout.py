"""Plot the local browser experiment and describe realized timer waits."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import tempfile

os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'secure-dns-browser-layout-mpl'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def q(values,p):
    a=sorted(values);x=(len(a)-1)*p;i=int(x);j=min(i+1,len(a)-1)
    return a[i]+(x-i)*(a[j]-a[i])


def active_wait_ms(gates):
    """Length of the union of intervals where at least one gate is waiting."""
    intervals = sorted((gate['start_ms'], gate['release_ms']) for gate in gates)
    start, end = intervals[0]
    total = 0.0
    for next_start, next_end in intervals[1:]:
        if next_start > end:
            total += end - start
            start, end = next_start, next_end
        else:
            end = max(end, next_end)
    return total + end - start


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,default=Path('data/browser-layout-2026-11-22'))
    p.add_argument('--results',type=Path,default=Path('results/browser-layout-2026-11-22'))
    p.add_argument('--figures',type=Path,default=Path('figures/browser-layout-2026-11-22'))
    p.add_argument('--doc',type=Path,default=Path('docs/BROWSER_LAYOUT.md'))
    args=p.parse_args()
    rows=[json.loads(line) for line in (args.data/'pages.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    summary=json.loads((args.results/'summary.json').read_text(encoding='utf-8'))
    if summary['counts']['invalid'] or len(rows)!=summary['counts']['attempted']: raise ValueError('Incomplete or invalid analysis')
    with (args.results/'paired_observations.csv').open(encoding='utf-8') as f: pairs=list(csv.DictReader(f))
    added=max(r['extra'] for r in rows)
    groups=[];page_waits={}
    for layout in ['parallel','sequential']:
        for extra in [0,added]:
            selected=[r for r in rows if r['layout']==layout and r['extra']==extra]
            waits=[g['actual_wait_ms'] for r in selected for g in r['gates']]
            page_medians=[statistics.median(g['actual_wait_ms'] for g in r['gates']) for r in selected]
            requested=selected[0]['requested_gate_ms']
            overshoot=[v-requested for v in waits]
            page_waits[(layout,extra)]=page_medians
            groups.append({'layout':layout,'extra_ms':extra,'requested_gate_ms':requested,'pages':len(selected),'gates':len(waits),'median_gate_wait_ms':statistics.median(waits),'gate_wait_q1_ms':q(waits,.25),'gate_wait_q3_ms':q(waits,.75),'gate_wait_p95_ms':q(waits,.95),'min_gate_wait_ms':min(waits),'max_gate_wait_ms':max(waits),'median_overshoot_ms':statistics.median(overshoot),'median_of_page_median_gate_wait_ms':statistics.median(page_medians)})
    with (args.results/'gate_wait_summary.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(groups[0]));writer.writeheader();writer.writerows(groups)
    by_condition={layout:{'baseline':next(g for g in groups if g['layout']==layout and g['extra_ms']==0),'added':next(g for g in groups if g['layout']==layout and g['extra_ms']==added)} for layout in ['parallel','sequential']}
    timing = {(row['layout'], row['rep'], row['extra']): active_wait_ms(row['gates']) for row in rows}
    union_pairs = [
        {'layout': layout, 'rep': rep, 'baseline_ms': duration,
         'added_ms': timing[layout, rep, added], 'delta_ms': timing[layout, rep, added] - duration}
        for (layout, rep, extra), duration in sorted(timing.items()) if extra == 0
    ]
    with (args.results/'paired_gate_union.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(union_pairs[0]));writer.writeheader();writer.writerows(union_pairs)
    union = {layout: statistics.median(row['delta_ms'] for row in union_pairs if row['layout'] == layout)
             for layout in ['parallel', 'sequential']}
    (args.results/'gate_wait_summary.json').write_text(json.dumps({'definition':'All gate wait summaries are descriptive. Seven gates from each page share timing conditions. Plot points use each navigation\'s median gate wait. Overshoot includes timer and event-loop scheduling; its physical cause is not isolated.','conditions':groups,'by_condition':by_condition,'median_paired_gate_union_delta_ms':union},indent=2)+'\n',encoding='utf-8')
    fig,axes=plt.subplots(1,2,figsize=(10.3,4.3),gridspec_kw={'width_ratios':[1,1.25]})
    color={'parallel':'#20649b','sequential':'#b45022'}
    rng=random.Random(20261122)
    for i,layout in enumerate(['parallel','sequential']):
        data=[float(r['delta_ms']) for r in pairs if r['layout']==layout]
        axes[0].scatter([i+rng.uniform(-.08,.08) for _ in data],data,s=23,color=color[layout],alpha=.55,zorder=2)
        e=next(x for x in summary['paired_effects'] if x['layout']==layout)
        m=e['median_paired_delta_ms']
        axes[0].errorbar(i,m,yerr=[[m-e['ci95_low_ms']],[e['ci95_high_ms']-m]],fmt='D',color='#111111',capsize=5,markersize=5,zorder=3)
    axes[0].set_xticks([0,1],['Parallel','Sequential'])
    axes[0].axhline(0,color='#888888',lw=.8)
    axes[0].set_ylabel('Paired completion difference (ms)')
    axes[0].set_title('A  Additional gate delay effect',loc='left',fontsize=11)
    positions=[];labels=[];values=[]
    for i,layout in enumerate(['parallel','sequential']):
        for j,extra in enumerate([0,added]):
            pos=i*3+j;positions.append(pos)
            vals=page_waits[(layout,extra)];values.append(vals)
            requested=next(g['requested_gate_ms'] for g in groups if g['layout']==layout and g['extra_ms']==extra)
            labels.append(f'{layout.title()}\n{requested:.0f} ms requested')
            axes[1].scatter([pos+rng.uniform(-.10,.10) for _ in vals],vals,s=19,alpha=.5,color=color[layout],zorder=2)
    axes[1].boxplot(values,positions=positions,widths=.45,whis=(0,100),showfliers=False,medianprops={'color':'black','linewidth':1.5},boxprops={'color':'#555555'},whiskerprops={'color':'#777777'},capprops={'color':'#777777'})
    axes[1].set_xticks(positions,labels,fontsize=8)
    axes[1].set_ylabel('Median gate wait per navigation (ms)')
    axes[1].set_title('B  Gate waits by requested delay',loc='left',fontsize=11)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Controlled browser delay injection',fontsize=14,y=.98)
    fig.text(.02,.01,'80 local navigations, 20 randomized paired blocks. Panel A: conditional paired-bootstrap intervals. Synthetic waits; no live DNS.',fontsize=8)
    fig.tight_layout(rect=[0,.06,1,.93])
    args.figures.mkdir(parents=True,exist_ok=True)
    for ext in ['png','pdf','svg']: fig.savefig(args.figures/f'layout_delay_effects.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    marker='\n## Realized gate waits and supplementary figure\n'
    text=args.doc.read_text(encoding='utf-8').split(marker)[0].rstrip()+marker
    text+='\nNominal gate targets were 25 and 50 ms. Realized waits were measured independently from route-entry to release. The following pooled gate summaries are descriptive; gates within a page are correlated. Overshoot includes timer and event-loop scheduling and does not identify a particular operating-system mechanism.\n\n| Layout | Requested ms | Pages / gates | Median actual wait ms | Median overshoot ms | Actual wait IQR ms |\n| --- | ---: | ---: | ---: | ---: | --- |\n'
    for g in groups: text+=f"| {g['layout']} | {g['requested_gate_ms']:.0f} | {g['pages']} / {g['gates']} | {g['median_gate_wait_ms']:.2f} | {g['median_overshoot_ms']:+.2f} | [{g['gate_wait_q1_ms']:.2f}, {g['gate_wait_q3_ms']:.2f}] |\n"
    text+=f'\nFor each trial, the union of the seven timer intervals measures time with at least one gate waiting and counts overlap only once. In a descriptive secondary analysis, the median paired increase in this union was **{union["parallel"]:+.2f} ms** in the parallel layout and **{union["sequential"]:+.2f} ms** in the sequential layout. The [paired union data](../results/browser-layout-2026-11-22/paired_gate_union.csv) use the route timer. Browser completion uses the browser clock and includes dispatch, fulfillment and image handling.\n\n'
    text+='![Observed completion effects and realized gate waits](../figures/browser-layout-2026-11-22/layout_delay_effects.png)\n\nPanel A shows all paired completion changes and the layout-specific medians with conditional intervals. Panel B shows each navigation’s median actual gate wait, with boxes spanning the IQR and whiskers the full observed range. The figure contains measured browser outcomes under explicitly synthetic delay treatments.\n\n![Constant fixture after seven image completions](../data/browser-layout-2026-11-22/fixture-parallel.png)\n\nThe sequential and parallel screenshots have the same appearance because resource bytes and layout are fixed. Their execution dependencies differ. Raw execution snapshots and payload hashes are recorded in design.json. SHA256SUMS.txt in the raw-data directory covers the captured files, excluding itself. These local hashes detect subsequent changes.\n'
    args.doc.write_text(text,encoding='utf-8')
    metadata={'inputs':[str(args.data/'pages.jsonl'),str(args.results/'summary.json'),str(args.results/'paired_observations.csv')],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'figure_stem':str(args.figures/'layout_delay_effects'),'matplotlib':matplotlib.__version__,'raw_navigations':len(rows),'gate_summaries':groups}
    (args.results/'plot_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(groups,indent=2))

if __name__=='__main__': main()
