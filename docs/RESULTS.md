# Historical results and figure guide

These tables describe the 15 and 19 November collections. Positive paired differences indicate slower DoH. Failures remain in attempt counts and successful-latency estimates condition on success.

See [the follow-up socket control and prediction results](CONTROL_RESULTS.md) and [the browser phase analysis](BROWSER_PHASES.md) for the revised paper.

| Date | Measured lookup attempts | Page attempts | Lookup priming records | Failed measured attempts |
|---|---:|---:|---:|---:|
| 2026-11-15 | 1800 | 360 | 120 | 0 |
| 2026-11-19 | 1800 | 360 | 120 | 0 |

## Session 2026-11-15

### Lookup distributions

| Provider | Mode | Success / attempts | Median ms | IQR ms | p95 ms | Paired difference ms [95% interval] |
|---|---|---:|---:|---:|---:|---|
| Cloudflare | UDP | 300/300 | 19.5 | 1.9 | 24.2 | Baseline |
| Cloudflare | DoH fresh | 300/300 | 68.1 | 6.3 | 79.3 | +48.4 [+47.7, +48.9] |
| Cloudflare | DoH established | 300/300 | 17.8 | 1.8 | 22.5 | -1.8 [-2.0, -1.4] |
| Google | UDP | 300/300 | 36.5 | 4.8 | 46.2 | Baseline |
| Google | DoH fresh | 300/300 | 134.9 | 42.3 | 152.9 | +84.6 [+70.3, +98.8] |
| Google | DoH established | 300/300 | 43.8 | 12.9 | 52.8 | +7.1 [+6.6, +7.8] |

### Controlled page load distributions

| Provider | Hostnames | Mode | Success / attempts | Median ms | p95 ms | Paired difference ms [95% interval] |
|---|---:|---|---:|---:|---:|---|
| Cloudflare | 1 | UDP | 30/30 | 44.2 | 49.2 | Baseline |
| Cloudflare | 1 | DoH fresh | 30/30 | 92.2 | 139.6 | +48.1 [+46.5, +51.5] |
| Cloudflare | 1 | DoH established | 30/30 | 44.5 | 51.0 | +1.6 [-0.6, +2.2] |
| Cloudflare | 8 | UDP | 30/30 | 65.4 | 78.0 | Baseline |
| Cloudflare | 8 | DoH fresh | 30/30 | 117.5 | 138.4 | +49.4 [+46.0, +55.9] |
| Cloudflare | 8 | DoH established | 30/30 | 67.9 | 82.9 | +1.9 [-1.5, +5.6] |
| Google | 1 | UDP | 30/30 | 60.6 | 71.2 | Baseline |
| Google | 1 | DoH fresh | 30/30 | 164.6 | 178.2 | +103.3 [+92.3, +105.5] |
| Google | 1 | DoH established | 30/30 | 70.7 | 79.8 | +10.4 [+3.9, +12.6] |
| Google | 8 | UDP | 30/30 | 100.9 | 114.5 | Baseline |
| Google | 8 | DoH fresh | 30/30 | 212.4 | 242.2 | +107.0 [+64.0, +117.0] |
| Google | 8 | DoH established | 30/30 | 100.0 | 133.1 | +0.7 [-3.6, +17.7] |

### Established lookup contrasts by window

| Provider | Window | Matched pairs | Median paired difference ms |
|---|---:|---:|---:|
| Cloudflare | 1 | 100 | -1.3 |
| Cloudflare | 2 | 100 | -1.8 |
| Cloudflare | 3 | 100 | -1.9 |
| Google | 1 | 100 | +9.6 |
| Google | 2 | 100 | -5.1 |
| Google | 3 | 100 | +8.7 |

### Dependence and sign sensitivity

| Provider | Lookup contrast | Domain-cluster interval ms | Positive paired fraction | Window sign reversal |
|---|---|---|---:|---|
| Cloudflare | DoH fresh | [+47.7, +48.9] | 99.7% | False |
| Cloudflare | DoH established | [-2.0, -1.5] | 22.7% | False |
| Google | DoH fresh | [+70.0, +98.1] | 99.0% | False |
| Google | DoH established | [+6.7, +7.5] | 70.3% | True |

The cluster interval resamples ten observed hostname clusters. It is a secondary conditional sensitivity, not a solution to temporal dependence. Sign fractions describe matched samples and are not hypothesis-test p-values. All values are retained without trimming.

[Full primary summary](../results/summary.json) · [Window effects](../results/window_effects.csv) · [Leave-one-window-out](../results/leave_one_window_out.csv) · [Domain effects](../results/domain_effects.csv) · [Robustness details](../results/robustness.json)

## Session 2026-11-19

### Lookup distributions

| Provider | Mode | Success / attempts | Median ms | IQR ms | p95 ms | Paired difference ms [95% interval] |
|---|---|---:|---:|---:|---:|---|
| Cloudflare | UDP | 300/300 | 20.8 | 4.0 | 32.1 | Baseline |
| Cloudflare | DoH fresh | 300/300 | 71.6 | 8.8 | 112.4 | +50.1 [+49.3, +51.1] |
| Cloudflare | DoH established | 300/300 | 19.6 | 3.7 | 29.2 | -1.3 [-1.9, -0.8] |
| Google | UDP | 300/300 | 37.5 | 5.9 | 51.2 | Baseline |
| Google | DoH fresh | 300/300 | 135.5 | 41.8 | 158.0 | +91.2 [+72.9, +99.0] |
| Google | DoH established | 300/300 | 44.2 | 13.8 | 56.5 | +5.3 [+4.6, +6.4] |

### Controlled page load distributions

| Provider | Hostnames | Mode | Success / attempts | Median ms | p95 ms | Paired difference ms [95% interval] |
|---|---:|---|---:|---:|---:|---|
| Cloudflare | 1 | UDP | 30/30 | 45.8 | 107.6 | Baseline |
| Cloudflare | 1 | DoH fresh | 30/30 | 96.6 | 130.2 | +49.5 [+45.1, +55.0] |
| Cloudflare | 1 | DoH established | 30/30 | 47.0 | 64.9 | +0.3 [-0.9, +2.2] |
| Cloudflare | 8 | UDP | 30/30 | 73.5 | 98.7 | Baseline |
| Cloudflare | 8 | DoH fresh | 30/30 | 121.9 | 144.8 | +50.7 [+44.2, +55.9] |
| Cloudflare | 8 | DoH established | 30/30 | 74.2 | 115.8 | +0.7 [-5.7, +6.0] |
| Google | 1 | UDP | 30/30 | 63.4 | 92.5 | Baseline |
| Google | 1 | DoH fresh | 30/30 | 165.3 | 192.1 | +88.4 [+66.1, +105.2] |
| Google | 1 | DoH established | 30/30 | 72.4 | 89.8 | +4.5 [+0.2, +10.1] |
| Google | 8 | UDP | 30/30 | 105.9 | 150.6 | Baseline |
| Google | 8 | DoH fresh | 30/30 | 211.9 | 289.2 | +101.9 [+61.8, +114.6] |
| Google | 8 | DoH established | 30/30 | 121.2 | 171.7 | +9.5 [-2.5, +15.4] |

### Established lookup contrasts by window

| Provider | Window | Matched pairs | Median paired difference ms |
|---|---:|---:|---:|
| Cloudflare | 1 | 100 | -1.4 |
| Cloudflare | 2 | 100 | -0.8 |
| Cloudflare | 3 | 100 | -1.7 |
| Google | 1 | 100 | +8.5 |
| Google | 2 | 100 | +10.0 |
| Google | 3 | 100 | -5.9 |

### Dependence and sign sensitivity

| Provider | Lookup contrast | Domain-cluster interval ms | Positive paired fraction | Window sign reversal |
|---|---|---|---:|---|
| Cloudflare | DoH fresh | [+49.2, +51.2] | 99.7% | False |
| Cloudflare | DoH established | [-2.2, -0.8] | 35.3% | False |
| Google | DoH fresh | [+79.9, +97.2] | 100.0% | False |
| Google | DoH established | [+4.6, +6.3] | 66.7% | True |

The cluster interval resamples ten observed hostname clusters. It is a secondary conditional sensitivity, not a solution to temporal dependence. Sign fractions describe matched samples and are not hypothesis-test p-values. All values are retained without trimming.

[Full primary summary](../results/replication-2026-11-19/summary.json) · [Window effects](../results/replication-2026-11-19/window_effects.csv) · [Leave-one-window-out](../results/replication-2026-11-19/leave_one_window_out.csv) · [Domain effects](../results/replication-2026-11-19/domain_effects.csv) · [Robustness details](../results/replication-2026-11-19/robustness.json)

## Figure guide

### lookup_ecdf 2026-11-15

Empirical cumulative distributions of successful direct lookup latency on 2026-11-15. Each provider/mode has 300 observations in the distributed complete dataset. Fresh DoH creates a new connection per query; established DoH reuses one connection per provider/window. Every successful observation is shown; tails are not trimmed.

![lookup_ecdf 2026-11-15](../figures/lookup_ecdf.png)

[Vector PDF](../figures/lookup_ecdf.pdf) · [SVG](../figures/lookup_ecdf.svg)

### lookup_paired_distributions 2026-11-15

Each dot is a successful matched DoH-minus-UDP difference. Vertical jitter only separates overlapping dots. Boxes span the interquartile range, central lines show medians, and whiskers span the complete observed range. Axes vary between panels to expose established-session variation. No outlier is excluded.

![lookup_paired_distributions 2026-11-15](../figures/lookup_paired_distributions.png)

[Vector PDF](../figures/lookup_paired_distributions.pdf) · [SVG](../figures/lookup_paired_distributions.svg)

### window_effects 2026-11-15

Median matched lookup differences calculated separately for each of the three nearby windows. Lines join observed medians as a visual guide, not a temporal model. Panels have separate vertical scales. A sign reversal in established-session differences is evidence of sensitivity within the sampled session, even when the pooled conditional interval excludes zero.

![window_effects 2026-11-15](../figures/window_effects.png)

[Vector PDF](../figures/window_effects.pdf) · [SVG](../figures/window_effects.svg)

### domain_effects 2026-11-15

Each point is a domain-specific median paired lookup difference across its repetitions and three windows. Provider markers are vertically offset for legibility. Panels have separate horizontal scales. The ten chosen names are a fixed workload, not a random sample of all Internet domains.

![domain_effects 2026-11-15](../figures/domain_effects.png)

[Vector PDF](../figures/domain_effects.pdf) · [SVG](../figures/domain_effects.svg)

### page_effects 2026-11-15

Median paired fixture load-event differences relative to UDP, with the original descriptive 95% within-window paired-bootstrap intervals. Each condition contains thirty matched navigations. Fresh DoH opens one shared connection per page; established setup occurs before navigation. These are fixed local-content DNS-gated browser loads, not native-browser DoH or general website performance.

![page_effects 2026-11-15](../figures/page_effects.png)

[Vector PDF](../figures/page_effects.pdf) · [SVG](../figures/page_effects.svg)

### setup_breakdown 2026-11-15

Medians and interquartile ranges of the recorded connection stage, remaining time (individual elapsed minus connection time), and total fresh lookup time. Marginal medians are shown separately and must not be added. The connection stage includes networking and client handling of TCP/TLS/HTTP2 setup; neither component isolates cryptographic CPU cost.

![setup_breakdown 2026-11-15](../figures/setup_breakdown.png)

[Vector PDF](../figures/setup_breakdown.pdf) · [SVG](../figures/setup_breakdown.svg)

### timing_series 2026-11-15

Every successful measured lookup plotted against its actual start time relative to the first measured lookup. Gaps separate the three measurement windows. No smoothing, time interpolation or outlier removal is applied. Chronological changes can be shared by neighboring trials and limit independence.

![timing_series 2026-11-15](../figures/timing_series.png)

[Vector PDF](../figures/timing_series.pdf) · [SVG](../figures/timing_series.svg)

### lookup_ecdf 2026-11-19

Empirical cumulative distributions of successful direct lookup latency on 2026-11-19. Each provider/mode has 300 observations in the distributed complete dataset. Fresh DoH creates a new connection per query; established DoH reuses one connection per provider/window. Every successful observation is shown; tails are not trimmed.

![lookup_ecdf 2026-11-19](../figures/replication-2026-11-19/lookup_ecdf.png)

[Vector PDF](../figures/replication-2026-11-19/lookup_ecdf.pdf) · [SVG](../figures/replication-2026-11-19/lookup_ecdf.svg)

### lookup_paired_distributions 2026-11-19

Each dot is a successful matched DoH-minus-UDP difference. Vertical jitter only separates overlapping dots. Boxes span the interquartile range, central lines show medians, and whiskers span the complete observed range. Axes vary between panels to expose established-session variation. No outlier is excluded.

![lookup_paired_distributions 2026-11-19](../figures/replication-2026-11-19/lookup_paired_distributions.png)

[Vector PDF](../figures/replication-2026-11-19/lookup_paired_distributions.pdf) · [SVG](../figures/replication-2026-11-19/lookup_paired_distributions.svg)

### window_effects 2026-11-19

Median matched lookup differences calculated separately for each of the three nearby windows. Lines join observed medians as a visual guide, not a temporal model. Panels have separate vertical scales. A sign reversal in established-session differences is evidence of sensitivity within the sampled session, even when the pooled conditional interval excludes zero.

![window_effects 2026-11-19](../figures/replication-2026-11-19/window_effects.png)

[Vector PDF](../figures/replication-2026-11-19/window_effects.pdf) · [SVG](../figures/replication-2026-11-19/window_effects.svg)

### domain_effects 2026-11-19

Each point is a domain-specific median paired lookup difference across its repetitions and three windows. Provider markers are vertically offset for legibility. Panels have separate horizontal scales. The ten chosen names are a fixed workload, not a random sample of all Internet domains.

![domain_effects 2026-11-19](../figures/replication-2026-11-19/domain_effects.png)

[Vector PDF](../figures/replication-2026-11-19/domain_effects.pdf) · [SVG](../figures/replication-2026-11-19/domain_effects.svg)

### page_effects 2026-11-19

Median paired fixture load-event differences relative to UDP, with the original descriptive 95% within-window paired-bootstrap intervals. Each condition contains thirty matched navigations. Fresh DoH opens one shared connection per page; established setup occurs before navigation. These are fixed local-content DNS-gated browser loads, not native-browser DoH or general website performance.

![page_effects 2026-11-19](../figures/replication-2026-11-19/page_effects.png)

[Vector PDF](../figures/replication-2026-11-19/page_effects.pdf) · [SVG](../figures/replication-2026-11-19/page_effects.svg)

### setup_breakdown 2026-11-19

Medians and interquartile ranges of the recorded connection stage, remaining time (individual elapsed minus connection time), and total fresh lookup time. Marginal medians are shown separately and must not be added. The connection stage includes networking and client handling of TCP/TLS/HTTP2 setup; neither component isolates cryptographic CPU cost.

![setup_breakdown 2026-11-19](../figures/replication-2026-11-19/setup_breakdown.png)

[Vector PDF](../figures/replication-2026-11-19/setup_breakdown.pdf) · [SVG](../figures/replication-2026-11-19/setup_breakdown.svg)

### timing_series 2026-11-19

Every successful measured lookup plotted against its actual start time relative to the first measured lookup. Gaps separate the three measurement windows. No smoothing, time interpolation or outlier removal is applied. Chronological changes can be shared by neighboring trials and limit independence.

![timing_series 2026-11-19](../figures/replication-2026-11-19/timing_series.png)

[Vector PDF](../figures/replication-2026-11-19/timing_series.pdf) · [SVG](../figures/replication-2026-11-19/timing_series.svg)

### cross_date_comparison 2026-11-15, 2026-11-19

Independent date-specific median paired lookup differences and their original conditional within-window bootstrap intervals. Each date is analyzed separately and no pooled-date estimate is calculated. Axes vary between panels. Differences between sessions can reflect network, resolver, cache and background conditions; two dates do not identify a causal time trend or long-term population distribution.

![cross_date_comparison 2026-11-15, 2026-11-19](../figures/cross_date_comparison.png)

[Vector PDF](../figures/cross_date_comparison.pdf) · [SVG](../figures/cross_date_comparison.svg)


## Reading the evidence

The within-window and per-domain intervals condition on the observed time periods. Google established DoH changes sign within both historical dates. The [held-window analysis](CONTROL_RESULTS.md) measures how often the pooled sign transfers.

The browser fixture uses live DNS waiting and fixed local content. Runtime versions differ across dates. See [methods](METHODS.md) and [reproduction details](REPRODUCIBILITY.md).
