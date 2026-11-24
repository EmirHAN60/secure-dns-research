"""Scientific plots for the same-evening session extension; no invented points."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np

from plot_results import style,tidy

PROVIDERS=("cloudflare","google")
BASELINES=("udp_fresh","udp_bound")
NAMES={"cloudflare":"Cloudflare","google":"Google","udp_fresh":"Fresh UDP","udp_bound":"Bound UDP","doh_warm":"Established DoH"}
COLORS={"session-01":"#286D8B","session-02":"#BD602B","session-03":"#36846B"}
CAT={"below_negative_threshold":0,"inside_threshold_band":1,"above_positive_threshold":2}


def save(fig,out,stem,caption,manifest):
    for suffix in ("png","pdf","svg"):
        fig.savefig(out/f"{stem}.{suffix}",dpi=220,metadata={"Creator":"Recorded session extension analysis"} if suffix=="pdf" else None)
    manifest.append({"stem":stem,"caption":caption,"width_inches":6.5,"png_dpi":220,
                     "files":[f"{stem}.{suffix}" for suffix in ("png","pdf","svg")],"source":"results/session_extension/summary.json"})
    plt.close(fig)


def own(rows,provider,baseline):
    return [r for r in rows if r["provider"]==provider and r["comparison"]=="doh_warm" and r["baseline"]==baseline and r["metric"]=="elapsed_ms"]


def effects(s,out,manifest):
    fig,axes=plt.subplots(2,2,figsize=(6.5,5.7),sharey="row",layout="constrained")
    sessions=s["sessions"]
    for row,provider in enumerate(PROVIDERS):
        for col,baseline in enumerate(BASELINES):
            ax=axes[row,col]
            ax.axhspan(-2,2,color="#EFE7DB",zorder=0)
            ax.axhspan(-1,1,color="#E1ECE7",zorder=0)
            ax.axhline(0,color="#777777",linewidth=.7)
            forecast=next(r for r in s["prospective_summary"] if r["provider"]==provider and r["baseline"]==baseline)
            ax.axhline(forecast["forecast_point_ms"],color="#555555",linestyle="--",linewidth=1)
            for x,session in enumerate(sessions,1):
                sid=session["session_id"]
                w=[r for r in own(s["window_effects"],provider,baseline) if r["session_id"]==sid]
                e=[r for r in own(s["session_effects"],provider,baseline) if r["session_id"]==sid]
                if e:
                    offsets=np.linspace(-.11,.11,len(w))
                    ax.scatter(x+offsets,[r["median_delta_ms"] for r in w],s=20,color="#87939C",alpha=.8,zorder=3)
                    ax.scatter(x,e[0]["median_delta_ms"],marker="D",s=43,color=COLORS[sid],edgecolors="white",linewidth=.5,zorder=4)
                else:
                    ax.text(x,.96,"pending",transform=ax.get_xaxis_transform(),ha="center",va="top",fontsize=10,color="#777777")
            ax.set(title=f"{NAMES[provider]} − {NAMES[baseline]}",xticks=[1,2,3],xticklabels=["S01","S02","S03"],xlim=(.6,3.4))
            if col==0:ax.set_ylabel("Median paired difference (ms)")
            tidy(ax)
    fig.legend(handles=[Line2D([],[],marker="o",linestyle="none",color="#87939C",label="Window median"),
                        Line2D([],[],marker="D",linestyle="none",color="#333333",label="Session median"),
                        Line2D([],[],linestyle="--",color="#555555",label="Frozen Nov20 forecast"),
                        Patch(facecolor="#E1ECE7",label="±1 ms sensitivity band"),Patch(facecolor="#EFE7DB",label="±2 ms sensitivity band")],
               loc="outside lower center",ncol=2,frameon=False,columnspacing=1,handletextpad=.4)
    fig.suptitle("Established DoH effects across spaced sessions")
    save(fig,out,"session_effects","Diamonds show session medians of paired established-DoH minus UDP differences; smaller grey dots show every observed window median. The dashed line is the fixed Nov20 calibration forecast, kept separate from new observations. Shading marks illustrative ±1 and ±2 ms sensitivity bands, not equivalence or utility limits. Missing/running sessions are labeled and contribute no outcome points. Three scheduled sessions occur on one evening, not on independent days.",manifest)


def threshold_decisions(s,out,manifest):
    threshold=s["thresholds"]["values_ms"]
    conditions=[(p,b) for p in PROVIDERS for b in BASELINES]
    a=np.full((len(conditions),4*(len(s["sessions"])+1)),np.nan)
    for y,(p,b) in enumerate(conditions):
        f=next(r for r in s["reference"]["calibration_forecasts"] if r["provider"]==p and r["baseline"]==b)
        for j,fc in enumerate(f["threshold_categories"]):a[y,j]=CAT[fc["category"]]
        for i,session in enumerate(s["sessions"],1):
            for j,t in enumerate(threshold):
                r=[r for r in own(s["thresholds"]["session_decisions"],p,b) if r["session_id"]==session["session_id"] and r["threshold_ms"]==t]
                if r:a[y,4*i+j]=CAT[r[0]["category"]]
    cmap=ListedColormap(["#8EB6C8","#E8E4D8","#CD895C"]);cmap.set_bad("#F4F4F4")
    fig,ax=plt.subplots(figsize=(6.5,3.6),layout="constrained")
    ax.imshow(a,cmap=cmap,norm=BoundaryNorm([-.5,.5,1.5,2.5],cmap.N),aspect="auto")
    labels={0:"L",1:"I",2:"H"}
    for y in range(a.shape[0]):
        for x in range(a.shape[1]):ax.text(x,y,labels[int(a[y,x])] if np.isfinite(a[y,x]) else "?",ha="center",va="center",fontsize=10)
    ax.set_yticks(range(4),[f"{NAMES[p]} / {'fresh' if b=='udp_fresh' else 'bound'}" for p,b in conditions])
    ax.set_xticks(range(a.shape[1]),[f"{t:g}" for _ in range(4) for t in threshold])
    ax.set_xlabel("Sensitivity threshold τ (ms)")
    top=ax.secondary_xaxis("top");top.set_xticks([1.5,5.5,9.5,13.5],["Nov20 forecast","Session 01","Session 02","Session 03"])
    for x in [3.5,7.5,11.5]:ax.axvline(x,color="white",linewidth=3)
    ax.tick_params(length=0);top.tick_params(length=0)
    fig.legend(handles=[Patch(facecolor="#8EB6C8",label="L: median below −τ"),Patch(facecolor="#E8E4D8",label="I: median inside ±τ"),Patch(facecolor="#CD895C",label="H: median above +τ")],
               loc="outside lower center",ncol=1,frameon=False)
    fig.suptitle("All predeclared thresholds: session decisions")
    save(fig,out,"session_threshold_decisions","Each cell categorizes the signed session paired median at a predeclared threshold of 0.5, 1, 2 or 5 ms. L means below −τ, I inside [−τ,+τ], and H above +τ; exact boundaries are inside. The first group is the frozen Nov20 forecast and the other groups are actual completed session statistics. Question marks indicate unavailable sessions. Inside-band medians do not establish equivalence, and these categories are not paired-observation exceedance rates.",manifest)


def magnitudes(s,out,manifest):
    fig,axes=plt.subplots(2,2,figsize=(6.5,4.8),sharey="row",layout="constrained")
    for row,p in enumerate(PROVIDERS):
        row_values=[max(r["median_abs_delta_ms"],r["abs_median_delta_ms"]) for b in BASELINES for r in own(s["session_effects"],p,b)]
        upper=max([2]+row_values)*1.22+.2
        for col,b in enumerate(BASELINES):
            ax=axes[row,col]
            for x,session in enumerate(s["sessions"],1):
                rs=[r for r in own(s["session_effects"],p,b) if r["session_id"]==session["session_id"]]
                if not rs:continue
                r=rs[0]
                ax.bar(x,r["median_abs_delta_ms"],width=.45,color="#D2A17F",zorder=2)
                ax.scatter(x,r["abs_median_delta_ms"],color="#252525",s=28,zorder=3)
                ax.annotate(f"{100*r['fraction_abs_gt_2ms']:.0f}%",(x,max(r["median_abs_delta_ms"],r["abs_median_delta_ms"])),xytext=(0,5),textcoords="offset points",ha="center",fontsize=10)
            ax.axhline(2,color="#777777",linewidth=.7,linestyle=":")
            ax.set(title=f"{NAMES[p]} − {NAMES[b]}",xticks=[1,2,3],xticklabels=["S01","S02","S03"],xlim=(.5,3.5),ylim=(0,upper))
            if col==0:ax.set_ylabel("Observed magnitude (ms)")
            tidy(ax)
    fig.legend(handles=[Patch(facecolor="#D2A17F",label="Median |paired difference|"),
                        Line2D([],[],marker="o",linestyle="none",color="#252525",label="|Median paired difference|")],loc="outside lower center",ncol=1,frameon=False)
    fig.suptitle("Pair magnitudes versus a signed summary")
    save(fig,out,"session_pair_magnitudes","Bars are medians of absolute individual paired differences; black dots are absolute values of the signed paired medians. Percentages are the fraction of complete pairs with |Δ| > 2 ms, with denominators reported in the numerical tables. These are different summaries: cancellation in a signed median does not mean individual pair differences are small. The dotted 2 ms reference is an illustrative sensitivity level.",manifest)


def google_marginals(s,out,manifest):
    fig=plt.figure(figsize=(6.5,5.2),layout="constrained");grid=fig.add_gridspec(2,2)
    top=fig.add_subplot(grid[0,:]);bottom=[fig.add_subplot(grid[1,i]) for i in (0,1)]
    colors={"udp_fresh":"#286D8B","udp_bound":"#36846B","doh_warm":"#BD602B"}
    allpoints=[p for g in s["exploratory_google_covariation"] for p in g["window_points"]]
    for mode in ("udp_fresh","udp_bound","doh_warm"):
        x=[];y=[]
        last_session=None
        for p in allpoints:
            if last_session is not None and p["session_id"]!=last_session:
                x.append(np.nan);y.append(np.nan)
            session=int(p["session_id"][-2:]);x.append((session-1)*4+p["window"]);y.append(p[mode+"_median_ms"])
            last_session=p["session_id"]
        if x:top.plot(x,y,marker="o",markersize=4,color=colors[mode],linewidth=1,label=NAMES[mode])
    ticks=[(i-1)*4+w for i in (1,2,3) for w in (1,2,3)]
    top.set(xticks=ticks,xticklabels=[f"{i}/{w}" for i in (1,2,3) for w in (1,2,3)],xlabel="Session / window",ylabel="Marginal median (ms)",title="Google whole-call marginal medians")
    top.legend(frameon=False,ncol=3,loc="best",handlelength=1.2,columnspacing=.8)
    tidy(top)
    for ax,baseline in zip(bottom,BASELINES):
        for session in s["sessions"]:
            points=[p for p in allpoints if p["session_id"]==session["session_id"]]
            if points:ax.scatter([p[baseline+"_centered_ms"] for p in points],[p["doh_warm_centered_ms"] for p in points],color=COLORS[session["session_id"]],s=32,zorder=3)
        ax.axhline(0,color="#999999",linewidth=.6);ax.axvline(0,color="#999999",linewidth=.6)
        ax.set(xlabel=f"Centered {NAMES[baseline]} (ms)",ylabel="Centered DoH (ms)")
        tidy(ax)
    fig.legend(handles=[Line2D([],[],marker="o",linestyle="none",color=COLORS[session["session_id"]],label=session["session_id"].replace("session-","Session ")) for session in s["sessions"] if session["status"]=="complete"],
               loc="outside lower center",ncol=3,frameon=False)
    fig.suptitle("Exploratory marginal co-movement, not mechanism")
    save(fig,out,"session_google_marginals","Top: each observed Google treatment marginal median by session/window. Lines only guide the eye; sampling gaps remain. Bottom: marginal window medians centered separately within each session and treatment. Point colors identify sessions. Correlation summaries are reported separately for verified build groups without p-values. Marginal co-movement cannot identify a cache, routing, resolver, CPU or packet-level mechanism; medians of paired differences remain distinct from differences of marginal medians.",manifest)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args()
    root=args.root.resolve();s=json.loads((root/"results/session_extension/summary.json").read_text(encoding="utf-8"));style()
    out=root/"figures";out.mkdir(exist_ok=True);manifest=[]
    if s["session_effects"]:
        effects(s,out,manifest);threshold_decisions(s,out,manifest);magnitudes(s,out,manifest);google_marginals(s,out,manifest)
    (out/"session_figure_manifest.json").write_text(json.dumps({"analysis_status":s["analysis_status"],"matplotlib_version":matplotlib.__version__,"figures":manifest},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"figures":len(manifest),"analysis_status":s["analysis_status"]}))


if __name__=="__main__":main()
