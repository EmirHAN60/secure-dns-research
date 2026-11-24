# Window sensitivity and UDP lifecycle control

Generated from retained actual measurements. Historical and explicit-bind control estimands remain separate.

## Historical six-window sensitivity

| Provider | Contrast | Pooled paired median ms | Fixed-window conditional interval ms | Median of window medians ms | Window range ms | Positive / negative windows |
|---|---|---:|---|---:|---|---|
| cloudflare | doh_fresh − UDP | +49.182 | [+48.728, +49.661] | +49.117 | [+48.312, +50.339] | 6 / 0 |
| cloudflare | doh_warm − UDP | -1.580 | [-1.884, -1.340] | -1.545 | [-1.911, -0.775] | 0 / 6 |
| google | doh_fresh − UDP | +90.400 | [+72.965, +97.956] | +94.597 | [+73.511, +98.882] | 6 / 0 |
| google | doh_warm − UDP | +6.445 | [+5.684, +6.967] | +8.630 | [-5.916, +9.952] | 4 / 2 |

The pooled historical statistic describes exactly these six fixed windows. Its conditional resampling interval resamples within each window while retaining every window. It is not a population confidence interval. Retrospective held-window and held-date checks reuse selected historical data; they are not a prospective prediction experiment. The median of window medians gives one weight to each observed window, a different statistic from the pooled pair median.

The interval holds the six selected windows fixed and does not estimate uncertainty across a population of network conditions. A narrow interval can coexist with a reversal of window-level sign.

## Retrospective held-window check

- cloudflare doh_fresh: training on the other five windows predicted the held window median's sign in 6/6 cases; mean absolute point-prediction error 1.035 ms versus 49.202 ms for a zero-adjustment forecast. These errors target window medians, not individual query times.
- cloudflare doh_warm: training on the other five windows predicted the held window median's sign in 6/6 cases; mean absolute point-prediction error 0.400 ms versus 1.482 ms for a zero-adjustment forecast. These errors target window medians, not individual query times.
- google doh_fresh: training on the other five windows predicted the held window median's sign in 6/6 cases; mean absolute point-prediction error 10.688 ms versus 89.248 ms for a zero-adjustment forecast. These errors target window medians, not individual query times.
- google doh_warm: training on the other five windows predicted the held window median's sign in 4/6 cases; mean absolute point-prediction error 7.176 ms versus 7.966 ms for a zero-adjustment forecast. These errors target window medians, not individual query times.

## Follow-up control

Status: complete.

Measured attempts: 6000; failed: 0; independently decoded valid records including priming: 6600.

| Provider | Comparison − baseline | Metric | Complete pairs | Pooled median ms | Window range ms | Positive / negative windows |
|---|---|---|---:|---:|---|---|
| cloudflare | udp_fresh − udp_bound | elapsed_ms | 1000 | +0.585 | [-0.629, +1.503] | 8 / 2 |
| cloudflare | udp_fresh − udp_bound | transport_elapsed_ms | 1000 | +0.409 | [-0.805, +1.339] | 7 / 3 |
| cloudflare | udp_fresh − udp_bound | post_bind_query_ms | 1000 | +0.414 | [-0.803, +1.340] | 7 / 3 |
| cloudflare | doh_warm − udp_bound | elapsed_ms | 1000 | -1.237 | [-2.848, +1.011] | 2 / 8 |
| cloudflare | doh_warm − udp_fresh | elapsed_ms | 1000 | -1.711 | [-3.687, -0.434] | 0 / 10 |
| google | udp_fresh − udp_bound | elapsed_ms | 1000 | -0.592 | [-3.091, +2.361] | 5 / 5 |
| google | udp_fresh − udp_bound | transport_elapsed_ms | 1000 | -0.755 | [-3.296, +2.198] | 4 / 6 |
| google | udp_fresh − udp_bound | post_bind_query_ms | 1000 | -0.754 | [-3.291, +2.201] | 4 / 6 |
| google | doh_warm − udp_bound | elapsed_ms | 1000 | -0.936 | [-7.961, +10.045] | 4 / 6 |
| google | doh_warm − udp_fresh | elapsed_ms | 1000 | -0.342 | [-7.248, +8.521] | 4 / 6 |

## Frozen Google sign check

The frozen positive-sign forecast matched 4/10 observed window medians; zero or opposite-sign medians: 6. The plan preceded every evaluated window: True.

The follow-up fresh UDP explicitly binds inside elapsed_ms; the historical client uses implicit bind. This is a prospective sign transport check under an implementation change, not exact validation of an identical estimator or a pure network/cryptography estimate.

elapsed_ms is the reported whole measured call: fresh UDP includes explicit create/bind; bound UDP and established DoH exclude already completed setup. transport_elapsed_ms is the common UDP send-call-to-receipt stage after bind, excluding validation. post_bind_query_ms is used only if explicitly recorded, never guessed from undocumented stage offsets. Persistent source-port/network/cache affinity and different protocol libraries remain alternative explanations.

## Replacing the UDP baseline within each window

- cloudflare: strict sign reversal in 2/10 windows; 0 windows have an exactly zero effect under at least one baseline. The difference of window effect medians ranges from -1.225 to +1.666 ms. The separate median paired fresh-minus-bound UDP shift ranges from -0.629 to +1.503 ms.
- google: strict sign reversal in 0/10 windows; 0 windows have an exactly zero effect under at least one baseline. The difference of window effect medians ranges from -3.384 to +2.309 ms. The separate median paired fresh-minus-bound UDP shift ranges from -3.091 to +2.361 ms.

All baseline-swap comparisons use the same complete three-treatment blocks within each window. The difference of effect medians must not be called the median paired shift. The per-block identity is (DoH − bound UDP) − (DoH − fresh UDP) = fresh UDP − bound UDP.

## Interpretation boundaries

No p-values or population confidence guarantees are used. Conditional resampling does not correct shared time effects, resolver-cache uncertainty or routing bias. Persistent UDP source ports may change network/cache affinity, so the fresh-versus-bound comparison does not isolate local CPU lifecycle cost. All successful values remain; failures are retained separately; no trimming or imputation occurs.
