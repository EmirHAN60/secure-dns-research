# Frozen remote DNS repeatability plan

Recorded 2026-11-23T21:48:19.752100+00:00 before A1 collection or outcomes. This is a local record, not an external preregistration. The JSON and source lock contain exact parameters and hashes.

## Runs and context

A1 is the first confirmed network context. B1 starts only after the user confirms switching. A2 is an optional return only if confirmed and collected. Every run uses the identical design and remains a separate analysis. No A-B-A label will be used unless all three occur. User labels and local configuration tags cannot establish independent physical routes, and fixed network order remains confounded with time. No raw network names or secrets are collected.

## Matched attempts and flow controls

Each run has three windows with 120-second target starts, two providers, ten domain names, and twelve four-attempt blocks per provider/name/window: all six 2UDP/2DoH orders under both repeat-flow and distinct-flow conditions. Totals are 2,880 measured and 240 priming attempts. Two UDP sockets and two H2 sessions per provider/window are established before timing. Distinct flows means different prepared client objects/ports, not statistical independence.

Four attempt starts target 0, 100, 200 and 300 ms within a block. Actual starts, completions and lateness determine analysis; timeouts and late starts remain. All six position pairs are retained. Same-mode differences are later minus earlier; cross-mode signed differences are DoH minus UDP.

## Primary lag and position comparison

Compare absolute UU, DD and DU differences for adjacent positions (1–2, 2–3, 3–4) whose actual measured starts are 75–125 ms apart. Comparability is across randomized balanced orders, not necessarily within each block. Use only common provider/window/domain/flow-condition/exact-position cells with all three pair classes represented. Give windows equal mass, cells equal mass within window and eligible pairs equal mass within class/cell. Report excluded cells, failures and late observations. Weighted medians use the empirical inverse-CDF definition in the JSON.

Report all 0.5, 1, 2 and 5 ms sensitivity thresholds. Compare observed magnitude summaries and exceedance fractions without subtracting a jitter median as a causal correction. Observations sharing attempts/blocks are dependent, so pair counts are not independent replication counts.

## Prespecified sensitivity and interpretation

Also show all adjacent lags, a 90–110 ms adjacent band, position separations two and three within 75–125% of their target lag, exact position strata, chronological cross-mode direction and all window/flow results. Empty strata remain explicit. No population/equivalence intervals, p-values or causal network claim are planned. The contemporaneous study cannot retroactively explain prior rates without stationarity assumptions.
