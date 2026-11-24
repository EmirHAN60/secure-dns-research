# Same-evening session extension results

Analysis status: **complete**. Completed audited sessions: 3/3.

All planned sessions remain in the status table. Running and missing sessions contribute no latency observations. Thresholds are sensitivity bands, not validated equivalence or utility bounds.

| Session | Scheduled start UTC | Actual start UTC | Status |
|---|---|---|---|
| session-01 | 2026-11-22T20:06:00+00:00 | 2026-11-22T20:06:20.451Z | complete |
| session-02 | 2026-11-22T20:18:00+00:00 | 2026-11-22T20:18:00.557Z | complete |
| session-03 | 2026-11-22T20:30:00+00:00 | 2026-11-22T20:30:00.549Z | complete |

Audited complete sessions contain 5,400 measured attempts and 540 priming records. Measured failures: 1. Failed durations are never substituted for successful lookup latencies or threshold differences.

- Retained failure: session-02, google / udp_bound, window 2, bbc.com: UDP response timeout.

## Established DoH minus pre-bound UDP

| Session | Provider | Pairs | Signed paired median ms | Median absolute paired difference ms | Fraction of pairs outside ±2 ms |
|---|---|---:|---:|---:|---:|
| session-01 | cloudflare | 300 | -1.824 | 2.278 | 0.583 |
| session-01 | google | 300 | +8.300 | 8.675 | 0.960 |
| session-02 | cloudflare | 300 | -1.092 | 2.156 | 0.533 |
| session-02 | google | 299 | +9.986 | 10.228 | 0.953 |
| session-03 | cloudflare | 300 | -2.030 | 2.577 | 0.620 |
| session-03 | google | 300 | +8.618 | 8.823 | 0.887 |

The signed paired median and the median absolute paired difference answer different questions. A signed median near zero can coexist with many individual paired differences exceeding a threshold. Pair rates do not equal rates of session/window medians.

## Fixed Nov20 calibration forecasts

The frozen point/sign/category forecasts were recorded before the new sessions. Historical data is not pooled into the new estimates. The source diff, full raw-input hash, source hashes and calibration snapshot are retained.

- cloudflare: fixed forecast -1.237 ms; mean absolute session-median error 0.508 ms versus 1.649 ms for zero adjustment; sign matched 3/3 sessions.
- google: fixed forecast -0.936 ms; mean absolute session-median error 9.904 ms versus 8.968 ms for zero adjustment; sign matched 0/3 sessions.

## Exploratory Google marginal readout

Observed Google whole-call window marginal medians were doh_warm: 32.106 to 47.872 ms (range 15.766); udp_fresh: 36.447 to 37.478 ms (range 1.031); udp_bound: 28.861 to 39.207 ms (range 10.346). These ranges show variation in measured client-and-service timings, but do not identify the responsible network path, cache, resolver, CPU or protocol stage. Per-session centered points and complete window values accompany this readout.

## Dependence and interpretation

Selected same-evening sessions; no multi-day or network population claim. No across-session confidence/equivalence interval. Within-session paired observations share domains/windows; rates describe retained successful pairs only. Cache/routing/source-port and unobserved conditions prevent mechanism attribution.

Complete numerical threshold grids, window medians, treatment marginals, paired counts, prospective category scores and retrospective leave-session checks are in `results/session_extension/`. Retrospective leave-session results are never described as issued forecasts. Exploratory Google marginal correlations cannot locate a resolver, routing, cache or CPU mechanism.
