# Remote same-mode repeatability controls

Each run remains separate. Weighted primary summaries compare successful adjacent-position pairs with observed start lag75–125ms in common cells. Windows, common cells within windows and eligible observations within class/cell receive equal respective weight. These are descriptive empirical distributions, not independent-pair population estimates.

| Run | Status | Measured attempts | Failures | Fully successful blocks |
|---|---|---:|---:|---:|
| A1 | complete | 2880 | 0 | 720 |
| B1 | complete | 2880 | 0 | 720 |
| A2 | complete | 2880 | 1 | 719 |

## Repeat-flow illustration at 2 ms

| Run | Provider | Common cells | Median abs. UU (ms) | Median abs. DD (ms) | Median abs. DU (ms) | UU >2ms | DD >2ms | DU >2ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A1 | cloudflare | 87 | 1.438 | 2.495 | 2.159 | 38.3% | 55.9% | 54.0% |
| A1 | google | 90 | 3.979 | 2.210 | 8.195 | 72.2% | 55.6% | 90.3% |
| B1 | cloudflare | 90 | 4.893 | 9.891 | 6.947 | 78.9% | 92.2% | 84.1% |
| B1 | google | 89 | 7.749 | 9.162 | 10.371 | 82.1% | 86.6% | 90.0% |
| A2 | cloudflare | 90 | 1.670 | 2.000 | 1.999 | 45.6% | 50.0% | 50.0% |
| A2 | google | 89 | 2.325 | 3.376 | 8.718 | 58.4% | 71.0% | 94.6% |

All percentages above use the frozen conditional weights; they need not equal an integer count divided by the pooled pair count when common-cell counts differ across windows. Primary lag/overlap exclusions are retained in each run's common_overlap.csv and summary.json, with all-lag sensitivity alongside the conditional primary analysis.

UU/DD are same-mode repeats; DU is DoH-minus-UDP before taking magnitude. All four thresholds and both flow conditions remain in the numerical outputs. Cross-mode magnitude is not corrected by subtracting a same-mode jitter median. Pair observations share blocks/attempts and are dependent.

## Scope and availability

This new study measures contemporaneous same-mode repeatability and cross-mode separation under matching position/lag strata. It cannot retrospectively explain old magnitude rates without stationarity assumptions, identify pure encryption/CPU cost, establish independent routes, deconvolve noise, or turn pair fractions into population probabilities. No p-values, population/equivalence CI, or causal network effect.

A1/B1/A2 denote planned user-confirmed contexts. A-B-A is described only when all three runs are actually collected. Fixed network order and elapsed time prevent a causal network-effect claim. No raw network names or secrets are required. Running and missing runs supply no inspected outcome data.
