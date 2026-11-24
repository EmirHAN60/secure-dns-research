"""Plot separate completed repeatability runs with descriptive uncertainty."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from plot_results import style,tidy

CLASSES=("UU","DD","DU")
COLORS={"UU":"#286D8B","DD":"#36846B","DU":"#BD602B"}
NAMES={"cloudflare":"Cloudflare","google":"Google"}
VIEWS=[("primary_adjacent_75_125ms","Primary"),("all_adjacent_lags","All"),("tight_adjacent_lag","Tight"),("position_separation_2","Lag2"),("position_separation_3","Lag3")]


def save(fig,out,stem,caption,manifest):
    out.mkdir(parents=True,exist_ok=True)
    for suffix in ("png","pdf","svg"):
        fig.canvas.draw()
        fig.savefig(out/f"{stem}.{suffix}",dpi=220,metadata={"Creator":"Recorded remote repeatability analysis"} if suffix=="pdf" else None)
    manifest.append({"stem":stem,"directory":out.as_posix(),"caption":caption,"png_dpi":220,"width_inches":float(fig.get_figwidth()),"height_inches":float(fig.get_figheight()),"files":[f"{stem}.{s}" for s in ("png","pdf","svg")]})
    plt.close(fig)


def panel_grid(runs):
    if len(runs)==1:
        fig,axes=plt.subplots(1,2,figsize=(6.5,3.8),squeeze=False)
        fig.subplots_adjust(left=.105,right=.98,bottom=.23,top=.80,wspace=.38)
        return fig,[(axes[0,i],runs[0],p) for i,p in enumerate(("cloudflare","google"))]
    fig,axes=plt.subplots(len(runs),2,figsize=(6.5,5.8 if len(runs)==2 else 8.0),squeeze=False)
    fig.subplots_adjust(left=.105,right=.98,bottom=.15 if len(runs)==2 else .11,top=.87 if len(runs)==2 else .90,wspace=.38,hspace=.75)
    return fig,[(axes[row,col],run,p) for row,run in enumerate(runs) for col,p in enumerate(("cloudflare","google"))]


def class_legend(fig):
    fig.legend(handles=[Line2D([],[],color=COLORS[c],marker="o",linewidth=1,label=label) for c,label in zip(CLASSES,["UU: UDP repeats","DD: DoH repeats","DU: cross-mode"])],loc="lower center",bbox_to_anchor=(.5,.005),ncol=3,frameon=False,columnspacing=1.0,handlelength=1.4)


def magnitudes(runs,out,manifest):
    fig,panels=panel_grid(runs)
    for ax,run,provider in panels:
        data=run["data"]
        for x,cls in enumerate(CLASSES):
            matches=[r for r in data["primary_classes"] if r["provider"]==provider and r["flow_condition"]=="repeat_flow" and r["pair_class"]==cls and r["estimate_status"]=="available"]
            if not matches:continue
            r=matches[0];m=r["weighted_median_abs_delta_ms"];lo=r["weighted_q25_abs_delta_ms"];hi=r["weighted_q75_abs_delta_ms"]
            ws=[w for w in data["window_primary_classes"] if w["provider"]==provider and w["flow_condition"]=="repeat_flow" and w["pair_class"]==cls and w["estimate_status"]=="available"]
            ax.scatter(x+np.linspace(-.09,.09,len(ws)),[w["weighted_median_abs_delta_ms"] for w in ws],s=18,color="#939EA6",alpha=.8,zorder=2)
            ax.errorbar(x,m,yerr=[[m-lo],[hi-m]],fmt="o",color=COLORS[cls],markersize=5,capsize=4,linewidth=1.4,zorder=3)
        ax.set(title=f"{run['run_id']} · {NAMES[provider]}",xticks=range(3),xticklabels=CLASSES,xlim=(-.45,2.45),ylim=(0,None),ylabel="Absolute difference (ms)")
        tidy(ax)
    class_legend(fig)
    fig.suptitle("Matched repeat-flow magnitudes")
    save(fig,out,"repeatability_magnitudes","Repeat-flow primary results: circles show weighted empirical median absolute pair differences and bars the weighted interquartile range, not a confidence interval. Grey dots show each observed window median. Only successful adjacent-position pairs with actual start lag75–125ms in common cells are represented. Windows/cells/classes use the frozen conditional weights. UU and DD are same-mode repeatability controls; DU is cross-mode separation. Runs remain separate and no jitter subtraction identifies causal encryption cost.",manifest)


def thresholds(runs,out,manifest):
    fig,panels=panel_grid(runs)
    for ax,run,provider in panels:
        values=[r for r in run["data"]["threshold_comparisons"] if r["provider"]==provider and r["flow_condition"]=="repeat_flow"]
        values.sort(key=lambda r:r["threshold_ms"])
        for cls in CLASSES:
            ax.plot([r["threshold_ms"] for r in values],[r[cls.lower()+"_fraction_abs_gt_threshold"] for r in values],marker="o",markersize=4,color=COLORS[cls],linewidth=1.4)
        ax.set(title=f"{run['run_id']} · {NAMES[provider]}",xticks=[.5,1,2,5],xticklabels=["0.5","1","2","5"],ylim=(0,1.03),xlabel="Sensitivity threshold (ms)",ylabel="Weighted fraction")
        tidy(ax)
    class_legend(fig)
    fig.suptitle("Same-mode and cross-mode exceedances")
    save(fig,out,"repeatability_thresholds","All four predeclared sensitivity thresholds for repeat-flow primary pairs. Rates use the same common-cell/window weights as the median comparison and need not equal a pooled integer count divided by pair count. They describe dependent observed pairs under the selected lag condition, not population probabilities, equivalence or user-perception limits. No cross-run pooling occurs.",manifest)


def lag_sensitivity(runs,out,manifest):
    fig,panels=panel_grid(runs)
    for ax,run,provider in panels:
        rows=run["data"]["primary_classes"]+run["data"]["sensitivity_classes"]
        for cls in CLASSES:
            y=[]
            for name,_ in VIEWS:
                match=[r for r in rows if r["provider"]==provider and r["flow_condition"]=="repeat_flow" and r["pair_class"]==cls and r["view"]==name and r["estimate_status"]=="available"]
                y.append(match[0]["weighted_median_abs_delta_ms"] if match else np.nan)
            ax.plot(range(5),y,marker="o",markersize=4,linewidth=1.2,color=COLORS[cls])
        ax.set(title=f"{run['run_id']} · {NAMES[provider]}",xticks=range(5),xticklabels=[label for _,label in VIEWS],ylabel="Median abs. difference (ms)",ylim=(0,None))
        ax.tick_params(axis="x",labelrotation=45)
        tidy(ax)
    class_legend(fig)
    fig.suptitle("Prespecified position and lag sensitivity")
    save(fig,out,"repeatability_lag_sensitivity","Repeat-flow weighted median magnitudes under primary adjacent75–125ms lags, all adjacent lags, tight adjacent90–110ms lags, and position separations2/3 within75–125%of their target lag. Each view recomputes common overlap and therefore can condition on a different set of cells; sample counts are retained. Lines only connect descriptive summaries. Missing overlap produces gaps, never an imputed estimate.",manifest)


def flow_comparison(run,out,manifest):
    fig,axes=plt.subplots(1,2,figsize=(6.5,3.7),sharey=True)
    fig.subplots_adjust(left=.08,right=.98,bottom=.31,top=.80,wspace=.25)
    for ax,provider in zip(axes,("cloudflare","google")):
        for condition,offset,color,marker in [("repeat_flow",-.12,"#286D8B","o"),("distinct_flows",.12,"#A34E81","D")]:
            for y,cls in enumerate(CLASSES):
                found=[r for r in run["data"]["primary_classes"] if r["provider"]==provider and r["flow_condition"]==condition and r["pair_class"]==cls and r["estimate_status"]=="available"]
                if not found:continue
                r=found[0];m=r["weighted_median_abs_delta_ms"];lo=r["weighted_q25_abs_delta_ms"];hi=r["weighted_q75_abs_delta_ms"]
                ax.errorbar(m,y+offset,xerr=[[m-lo],[hi-m]],fmt=marker,color=color,markersize=5,capsize=3,linewidth=1.3)
        ax.set(title=NAMES[provider],xlabel="Absolute difference (ms)",xlim=(0,None))
        tidy(ax,"x")
    axes[0].set_yticks(range(3),CLASSES);axes[0].invert_yaxis()
    fig.legend(handles=[Line2D([],[],marker="o",color="#286D8B",label="Repeated prepared flow"),Line2D([],[],marker="D",color="#A34E81",label="Distinct prepared flows")],loc="lower center",bbox_to_anchor=(.5,.005),ncol=1,frameon=False)
    fig.suptitle(f"{run['run_id']} · flow-condition sensitivity")
    save(fig,out,"repeatability_flow_comparison","Weighted median absolute pair differences and interquartile ranges under repeated or distinct prepared flows, in the same primary position/lag stratum. Distinct UDP/H2 objects and source ports are not assumed statistically independent or separate physical paths. Between-flow level differences and temporal variation can both contribute. Bars are IQRs, not uncertainty intervals for a population estimate.",manifest)


def fixed_flow_comparison(runs,out,manifest):
    """Compact manuscript view: both flow rules for DD and DU, without pooling runs."""
    fig,axes=plt.subplots(1,2,figsize=(6.5,3.3),sharex=True,sharey=True)
    fig.subplots_adjust(left=.08,right=.98,bottom=.33,top=.80,wspace=.20)
    combinations=[("DD","repeat_flow",-.24,"o","DD · same flow"),("DD","distinct_flows",-.08,"D","DD · distinct flows"),
                  ("DU","repeat_flow",.08,"o","DU · repeat-flow block"),("DU","distinct_flows",.24,"D","DU · distinct-flow block")]
    greatest=0
    for ax,provider in zip(axes,("cloudflare","google")):
        for y,run in enumerate(runs):
            for cls,condition,offset,marker,_ in combinations:
                found=[r for r in run["data"]["primary_classes"] if r["provider"]==provider and r["flow_condition"]==condition and r["pair_class"]==cls and r["estimate_status"]=="available"]
                if not found:continue
                value=found[0]["weighted_median_abs_delta_ms"];greatest=max(greatest,value)
                ax.scatter(value,y+offset,marker=marker,s=31,color=COLORS[cls],edgecolors="white",linewidths=.45,zorder=3)
        ax.set(title=NAMES[provider],xlabel="Median abs. difference (ms)",yticks=range(len(runs)),yticklabels=[r["run_id"] for r in runs],ylim=(-.55,len(runs)-.45))
        tidy(ax,"x")
    axes[0].set_xlim(0,max(1,greatest*1.12));axes[0].invert_yaxis()
    fig.legend(handles=[Line2D([],[],marker=marker,color=COLORS[cls],linestyle="none",label=label) for cls,_,_,marker,label in combinations],
               loc="lower center",bbox_to_anchor=(.5,.005),ncol=2,frameon=False,columnspacing=2.3,handletextpad=.5)
    fig.suptitle("Same versus distinct prepared flows")
    save(fig,out,"repeatability_fixed_flow_comparison","Separate-run weighted primary median absolute differences for same-mode DoH repeats (DD) and DoH-versus-UDP pairs (DU), under the same versus distinct prepared-flow rules. Both provider panels share the x scale. Matching and weighting are identical to the full results: adjacent successful pairs, actual start lag75–125ms, common position/domain/window cells and equal window mass. Points are descriptive estimates without confidence intervals; distinct flows do not establish independent routes. No cross-run pooling or jitter subtraction.",manifest)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();root=args.root.resolve()
    summary=json.loads((root/"results/repeatability/summary.json").read_text(encoding="utf-8"));runs=[]
    for r in summary["runs"]:
        if r["status"]=="complete":runs.append({**r,"data":json.loads((root/r["summary_path"]).read_text(encoding="utf-8"))})
    style();manifest=[];out=root/"figures"
    if runs:
        magnitudes(runs,out,manifest);thresholds(runs,out,manifest);lag_sensitivity(runs,out,manifest);fixed_flow_comparison(runs,out,manifest)
        for run in runs:
            own=out/"repeatability"/run["run_id"];magnitudes([run],own,manifest);thresholds([run],own,manifest);lag_sensitivity([run],own,manifest);flow_comparison(run,own,manifest)
    for item in manifest:item["directory"]=str(Path(item["directory"]).relative_to(root)).replace("\\","/")
    (out/"repeatability_figure_manifest.json").write_text(json.dumps({"matplotlib_version":matplotlib.__version__,"completed_runs":[r["run_id"] for r in runs],"figures":manifest},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"completed_runs":[r["run_id"] for r in runs],"figures":len(manifest)}))


if __name__=="__main__":main()
