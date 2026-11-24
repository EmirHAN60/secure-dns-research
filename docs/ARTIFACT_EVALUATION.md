# Artifact evaluation

Artifact version **1.2.0** accompanies the [paper](../Secure_DNS_Research_Paper.pdf) and its [Markdown source](paper_source.md). Use the release ZIP for a frozen file set and the repository for browsing the code. The release ZIP includes a file-level SHA-256 manifest. The outer ZIP checksum identifies the exact download.

## Check the artifact

1. Open a terminal in the extracted directory and run `python scripts/validate_package.py` with Python 3.12 or later. This checks hashes, collection status, artifact links and anchors, figure signatures, and required output files.
2. Install the pinned Python dependencies and run `python scripts/reproduce.py` with Node.js 22 or later on PATH. The [reproduction guide](REPRODUCIBILITY.md) lists dependencies and individual steps. The [execution log](evidence/verification.log) records the checks from the distributed build.
3. Compare the figure captions and result tables with the CSV or JSON files. Time and image metadata may change on regeneration. Compare counts and estimates for numerical verification. Use the frozen ZIP for exact byte comparison.

## Follow each claim to data

| Claim | Recorded input or plan | Reproducible result |
|---|---|---|
| Fresh setup can dominate early lookup time in the historical measurement. | [15 November records](../data/dns_raw.jsonl) and [19 November records](../data/replication-2026-11-19/dns_raw.jsonl) | [Paired contrasts with denominators](RESULTS.md) |
| The ready UDP baseline changes small public contrasts. | [20 November design](../data/control-2026-11-20/design.json) and [executed source](evidence/collection-source-2026-11-20/README.md) | [Whole-call and after-bind estimates](CONTROL_RESULTS.md) |
| Local setup is measurable with a fixed responder. | [Loopback attempt records](../data/loopback-2026-11-22/loopback_raw.jsonl) | [Local timing summary](LOOPBACK.md) |
| A frozen session forecast missed later effects. | [Original forecast](SESSION_EXTENSION_PLAN.json) and [additional-date plan](ADDITIONAL_DATE_PLAN.json) | [22 November scores](SESSION_EXTENSION_RESULTS.md) and [23 November scores](../results/additional_date.json) |
| Same-protocol repeats provide a reference for sequential query variation. | [Frozen design](REPEATABILITY_PLAN.md) and [capture and network context](evidence/repeatability-source-2026-11-23/README.md) | [Time and position matched comparison](REPEATABILITY_RESULTS.md) |
| Resource dependencies alter how a controlled wait accumulates. | [Browser fixture source](../data/browser-layout-2026-11-22/fixture.html) and [trial schedule](../data/browser-layout-2026-11-22/schedule.json) | [Delay and realized gate analysis](BROWSER_LAYOUT.md) |

Current collectors define their timing boundaries and derive pseudorandom streams from the collection seed, window and experiment identifier. Archive snapshots preserve the software used for earlier datasets. The [historical order audit](../results/historical_order_audit.json) found six distinct schedules across twelve observed windows. The repeated sequences remain in the historical analysis. The Node.js parser and the independent Python decoder both check question identity and a reachable address owner through the answer-section CNAME chain. Regression cases cover a matching question with an unrelated answer owner.

## Scope and provenance

The plans contain locally recorded precollection timestamps and source hashes. Their purpose is to make analytical decisions and software versions inspectable. The [limitations](LIMITATIONS.md) describe the available vantage points, dependencies across time and the browser workloads. See [related benchmarks](RELATED_BENCHMARKS.md) for the protocol choices this study inherits and the specific comparisons it adds.
