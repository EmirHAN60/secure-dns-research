"""Decompose the saved fixture's paired load differences at document response end."""

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


DATASETS = (
    ("2026-11-15", "data/pages.jsonl"),
    ("2026-11-19", "data/replication-2026-11-19/pages.jsonl"),
)
MODES = ("udp", "doh_fresh", "doh_reused")
METRICS = ("document", "after_document", "load")


def timeline(page):
    navigation = page["navigation"]
    start, response, load = (
        navigation[key] for key in ("startTime", "responseEnd", "loadEventEnd")
    )
    if not all(math.isfinite(value) for value in (start, response, load)):
        raise ValueError(f"Non-finite navigation time in {page['id']}")
    if not start <= response <= load or not math.isclose(load - start, page["plt_ms"]):
        raise ValueError(f"Inconsistent navigation timeline in {page['id']}")
    return response - start, load - response, load - start


def analyze(root):
    groups = defaultdict(list)
    for date, relative_file in DATASETS:
        blocks = defaultdict(dict)
        for line in (root / relative_file).read_text(encoding="utf-8").splitlines():
            page = json.loads(line)
            key = tuple(page[field] for field in ("provider", "origins", "window", "rep"))
            if page["mode"] in blocks[key]:
                raise ValueError(f"Duplicate browser attempt: {page['id']}")
            blocks[key][page["mode"]] = page

        for (provider, hosts, window, rep), block in blocks.items():
            if set(block) != set(MODES):
                raise ValueError(f"Incomplete browser block: {date} {provider} {hosts} {window} {rep}")
            for mode in MODES[1:]:
                key = (date, provider, hosts, mode)
                differences = None
                if block["udp"]["status"] == block[mode]["status"] == "ok":
                    differences = [
                        a - b for a, b in zip(timeline(block[mode]), timeline(block["udp"]))
                    ]
                groups[key].append(differences)

    rows = []
    for (date, provider, hosts, mode), attempts in sorted(groups.items()):
        complete = [values for values in attempts if values is not None]
        if not complete:
            raise ValueError(f"No successful navigation pairs: {date} {provider} {hosts} {mode}")
        row = dict(date=date, provider=provider, hostnames=hosts, treatment=mode,
                   attempted_pairs=len(attempts), complete_pairs=len(complete))
        row.update({f"{key}_delta_ms": median(values)
                    for key, values in zip(METRICS, zip(*complete))})
        rows.append(row)
    return rows


def plot(rows, output):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(9, 5.2), sharex=True, layout="constrained")
    treatments = ("doh_fresh", "doh_reused")
    labels = ("Through document response", "After document response", "Total to load event")
    styles = (("o", "#26627d"), ("s", "#af5b2a"), ("D", "#202827"))
    for ax, date, provider in zip(
        axes.flat,
        ("2026-11-15", "2026-11-15", "2026-11-19", "2026-11-19"),
        ("cloudflare", "google", "cloudflare", "google"),
    ):
        ax.set_title(f"{date[8:]} Nov · {provider.title()}", loc="left")
        ax.axvline(0, color="#7b8490", linewidth=1, zorder=0)
        ax.grid(axis="x", color="#e2e5e9", zorder=0)
        combinations = [(m, h) for m in treatments for h in (1, 8)]
        for y, (mode, hosts) in enumerate(combinations):
            row = next(r for r in rows if (r["date"], r["provider"], r["hostnames"], r["treatment"])
                       == (date, provider, hosts, mode))
            for offset, key, label, (marker, color) in zip(
                (-0.19, 0, 0.19), METRICS, labels, styles
            ):
                ax.scatter(row[f"{key}_delta_ms"], y + offset, marker=marker, color=color,
                           s=30, label=label if y == 0 else None, zorder=3)
        ax.set_yticks(range(4), ["Fresh · 1", "Fresh · 8", "Ready · 1", "Ready · 8"])
        ax.set_ylim(3.55, -0.55)
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper center", ncols=3, frameon=False,
               bbox_to_anchor=(0.5, 1))
    fig.get_layout_engine().set(rect=(0, 0, 1, 0.92))
    fig.supxlabel("Median paired difference vs UDP (ms)")
    for extension in ("png", "pdf", "svg"):
        fig.savefig(output.with_suffix(f".{extension}"), dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    root = parser.parse_args().root
    rows = analyze(root)
    with (root / "results/browser_phases.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    plot(rows, root / "figures/browser_phases")
    print(f"Decomposed {len(rows)} browser comparisons using saved navigation timing.")


if __name__ == "__main__":
    main()
