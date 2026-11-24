"""Window-level scientific figures for the historical and UDP-control analyses."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from plot_results import style, tidy

PROVIDERS=("cloudflare","google")
NAMES={"cloudflare":"Cloudflare","google":"Google"}


def save(fig,out,stem,caption,manifest):
    for extension in ("png","pdf","svg"):
        fig.savefig(out/f"{stem}.{extension}",dpi=220,
                    metadata={"Creator":"Recorded-window control analysis"} if extension=="pdf" else None)
    manifest.append({"stem":stem,"caption":caption,"width_inches":6.5,"png_dpi":220,
                     "files":[f"{stem}.{extension}" for extension in ("png","pdf","svg")],
                     "source":"results/control_analysis.json; recorded raw observations only"})
    plt.close(fig)


def historical(result,out,manifest):
    h=result["historical"]
    fig,axes=plt.subplots(2,2,figsize=(6.5,5.8),layout="constrained")
    for row,provider in enumerate(PROVIDERS):
        for col,mode in enumerate(("doh_fresh","doh_warm")):
            ax=axes[row,col]
            ws=[w for w in h["windows"] if w["provider"]==provider and w["comparison"]==mode]
            ws.sort(key=lambda w:w["window_key"])
            pooled=next(p for p in h["pooled_contrasts"] if p["provider"]==provider and p["comparison"]==mode)
            for x,w in enumerate(ws):
                ax.scatter(x,w["median_ms"],s=30,color="#286D8B" if w["date"]=="2026-11-15" else "#A34E81",zorder=3)
            med=pooled["pooled_median_ms"]
            lo,hi=pooled["conditional_fixed_window_interval_ms"]
            ax.errorbar(7,med,yerr=[[med-lo],[hi-med]],fmt="D",color="#BD602B",capsize=4,markersize=5,zorder=4)
            ax.axhline(pooled["median_of_window_medians_ms"],color="#333333",linestyle=":",linewidth=1.1)
            ax.axhline(0,color="#777777",linestyle="--",linewidth=.7)
            ax.set(title=f"{NAMES[provider]} · {'fresh' if mode=='doh_fresh' else 'established'}",
                   xticks=[0,1,2,3,4,5,7],xticklabels=[f"{w['date'][-2:]}/{w['window']}" for w in ws]+["Pool"],
                   xlim=(-.5,7.5))
            if col==0:ax.set_ylabel("DoH minus UDP (ms)")
            if row==1:ax.set_xlabel("November date / window")
            ax.tick_params(axis="x",labelrotation=35)
            tidy(ax)
    fig.legend(handles=[Line2D([],[],marker="o",linestyle="none",color="#286D8B",label="15 November windows"),
                        Line2D([],[],marker="o",linestyle="none",color="#A34E81",label="19 November windows"),
                        Line2D([],[],marker="D",linestyle="none",color="#BD602B",label="Fixed-window pooled interval"),
                        Line2D([],[],linestyle=":",color="#333333",label="Median of window medians")],
               loc="outside lower center",ncol=2,frameon=False,columnspacing=1,handletextpad=.4)
    fig.suptitle("Six observed windows versus pooled precision")
    save(fig,out,"historical_window_sensitivity",
         "Dots show six separate observed window medians, each based on 100 successful matched pairs. The orange diamond is the 600-pair pooled median with a conditional resampling interval that holds the selected windows and their sizes fixed. The dotted line is the equally weighted median of the six window medians, a different statistic. Panels have different vertical scales. The interval is not a population confidence guarantee; historical implicit-bind UDP is distinct from the follow-up control estimator.",manifest)


def control_windows(result,out,manifest):
    c=result["control"]
    fig,axes=plt.subplots(2,2,figsize=(6.5,5.9),layout="constrained")
    specs=[("udp_fresh","udp_bound","elapsed_ms","#286D8B","UDP: whole call","-"),
           ("udp_fresh","udp_bound","post_bind_query_ms","#BD602B","UDP: post-bind validated","--"),
           ("udp_fresh","udp_bound","transport_elapsed_ms","#36846B","UDP: send to receipt",":"),
           ("doh_warm","udp_bound","elapsed_ms","#A34E81","DoH minus bound UDP","-"),
           ("doh_warm","udp_fresh","elapsed_ms","#555555","DoH minus fresh UDP","--")]
    for row,provider in enumerate(PROVIDERS):
        for comparison,baseline,metric,color,label,linestyle in specs:
            ax=axes[row,0 if comparison=="udp_fresh" else 1]
            ws=[w for w in c["windows"] if w["provider"]==provider and w["comparison"]==comparison and w["baseline"]==baseline and w["metric"]==metric]
            ws.sort(key=lambda w:w["window"])
            if ws:ax.plot([w["window"] for w in ws],[w["median_ms"] for w in ws],marker="o",markersize=3.5,
                          linewidth=1.2,linestyle=linestyle,color=color,label=label)
        for col in (0,1):
            ax=axes[row,col]
            ax.axhline(0,color="#777777",linestyle="--",linewidth=.7)
            ax.set_title(f"{NAMES[provider]} · {'UDP control' if col==0 else 'DoH baseline'}")
            ax.set_xticks([1,3,5,7,9,10])
            if col==0:ax.set_ylabel("Median paired difference (ms)")
            if row==1:ax.set_xlabel("Follow-up window")
            tidy(ax)
    fig.legend(handles=[Line2D([],[],color=color,linestyle=linestyle,marker="o",markersize=4,label=label)
                        for _,_,_,color,label,linestyle in specs],
               loc="outside lower center",ncol=2,frameon=False,columnspacing=1,handletextpad=.4)
    fig.suptitle("Baseline and timing-stage sensitivity · 20 November")
    save(fig,out,"control_window_effects",
         "Each point is a median of matched within-window differences. Left panels compare fresh minus pre-bound UDP using three separately defined timers: whole call, post-bind send through validated response, and send through receipt. Right panels compare established DoH with fresh or bound UDP using whole measured calls. Setup is outside the bound UDP and established DoH timers. Lines connect observed medians only. Persistent source ports, network/cache affinity and client implementation prevent assigning the differences purely to CPU lifecycle cost.",manifest)


def udp_stages(result,out,manifest):
    c=result["control"]
    fig,axes=plt.subplots(1,2,figsize=(6.5,3.8),sharey=True,layout="constrained")
    metrics=("elapsed_ms","post_bind_query_ms","transport_elapsed_ms")
    labels=["Whole call","Post-bind validated","Send to receipt"]
    for ax,provider in zip(axes,PROVIDERS):
        for y,metric in enumerate(metrics):
            r=next(r for r in c["paired_contrasts"] if r["provider"]==provider and r["comparison"]=="udp_fresh" and r["baseline"]=="udp_bound" and r["metric"]==metric)
            ax.hlines(y,r["window_median_min_ms"],r["window_median_max_ms"],color="#8A949D",linewidth=2,zorder=1)
            ax.scatter(r["pooled_median_ms"],y,s=40,color="#286D8B",zorder=3)
            ax.scatter(r["median_of_window_medians_ms"],y,s=27,color="#BD602B",marker="D",zorder=4)
        ax.axvline(0,color="#777777",linestyle="--",linewidth=.7)
        ax.set(title=NAMES[provider],xlabel="Fresh minus bound UDP (ms)")
        tidy(ax,"x")
    axes[0].set_yticks(range(3),labels)
    axes[0].invert_yaxis()
    fig.legend(handles=[Line2D([],[],marker="o",color="#286D8B",linestyle="none",label="Pooled paired median"),
                        Line2D([],[],marker="D",color="#BD602B",linestyle="none",label="Median of window medians"),
                        Line2D([],[],color="#8A949D",linewidth=2,label="Observed window range")],
               loc="outside lower center",ncol=1,frameon=False)
    fig.suptitle("Fresh versus bound UDP: timer definition matters")
    save(fig,out,"control_udp_stages",
         "Fresh-minus-bound UDP contrasts using three timer definitions. Grey lines span observed window-median minima and maxima; they are not confidence intervals. Blue circles give the pooled median paired difference and orange diamonds give the median of window medians. The post-bind timers exclude socket creation/binding, with validation included only in the middle row. No timer is interpreted as pure local CPU cost.",manifest)


def sign_validation(result,out,manifest):
    h,c=result["historical"],result["control"]
    historical=[w for w in h["windows"] if w["provider"]=="google" and w["comparison"]=="doh_warm"]
    historical.sort(key=lambda w:w["window_key"])
    future=c["forecast_validation"]["observations"]
    fig,axes=plt.subplots(1,2,figsize=(6.5,3.8),sharey=True,layout="constrained")
    axes[0].scatter(range(1,len(historical)+1),[w["median_ms"] for w in historical],color="#286D8B",s=35,zorder=3)
    axes[0].set(title="Historical implicit-bind UDP",xticks=range(1,len(historical)+1),
                xticklabels=[f"{w['date'][-2:]}/{w['window']}" for w in historical],xlabel="November date / window")
    axes[0].set_ylabel("Google established DoH minus UDP (ms)")
    axes[1].scatter([f["window"] for f in future],[f["observed_median_ms"] for f in future],color="#BD602B",s=35,zorder=3)
    axes[1].set(title="Follow-up explicit-bind UDP",xticks=[1,3,5,7,9,10],xlabel="20 November window")
    forecast=c["forecast_validation"]
    axes[1].text(.03,.61,f"Frozen forecast: positive\nMatched {forecast['positive_sign_matches']}/{forecast['windows_evaluated']} windows",
                 transform=axes[1].transAxes,ha="left",va="top",fontsize=10,
                 bbox={"facecolor":"white","edgecolor":"none","alpha":.85})
    for ax in axes:
        ax.axhline(0,color="#555555",linestyle="--",linewidth=.8)
        tidy(ax)
    fig.suptitle("Transporting the historical Google sign forecast")
    save(fig,out,"google_sign_validation",
         "Historical and follow-up window medians use fresh UDP including setup. The positive-sign forecast for each follow-up window was frozen before collection and is evaluated without selecting windows after observing outcomes. Fresh UDP changed from implicit to explicit bind, and the operating-system release also changed, so this is a prospective sign transport check under changed conditions, not validation of an identical estimator or a causal calendar effect. All completed planned windows and their pair counts remain in the results.",manifest)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    root=args.root.resolve()
    result=json.loads((root/"results/control_analysis.json").read_text(encoding="utf-8"))
    out=root/"figures"
    out.mkdir(parents=True,exist_ok=True)
    style()
    manifest=[]
    historical(result,out,manifest)
    if result["control"]["status"]=="complete":
        control_windows(result,out,manifest)
        udp_stages(result,out,manifest)
        sign_validation(result,out,manifest)
    (out/"control_figure_manifest.json").write_text(json.dumps({"matplotlib_version":matplotlib.__version__,"figures":manifest},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"figures":len(manifest),"control_status":result["control"]["status"]}))


if __name__=="__main__":
    main()
