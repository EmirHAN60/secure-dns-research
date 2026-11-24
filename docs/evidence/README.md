# Execution and capture evidence

## Recorded-data verification

`verification.log` is captured stdout/stderr from `python scripts/reproduce.py`. The pipeline runs local tests, audits immutable saved inputs and transport conditions, recalculates the dates separately, builds figures and the manuscript, and checks package consistency. It does not collect Internet measurements.

`offline-verification.png` is an actual browser screenshot of a local HTML verification report. The report displays data-derived counts and captured command output. It is **not a screenshot of a terminal application**. The source HTML, exact log snapshot and capture metadata identify what was displayed. A later reproduction can update `verification.log`; the screenshot remains associated with its own retained source snapshot.

- [Browser screenshot](offline-verification.png)
- [Rendered report source](offline-verification.html)
- [Exact screenshot log snapshot](offline-verification-source.log)
- [Capture metadata](offline-verification.json)
- [Latest reproduction log](verification.log)

The screenshot's report can be recaptured with `node scripts/capture_evidence.mjs` after a successful reproduction and installation of the browser library. This optional image capture is outside the offline numerical pipeline. It does not alter measurements.

## Browser fixture screenshot

`fixture-eight-hostnames.png` was captured from an actual successful eight-hostname fixture navigation on 19 November 2026. Seven SVG images loaded after live DNS resolution. Provider, transport, page ID and capture time are recorded in `fixture-eight-hostnames.json`.

- [Fixture screenshot](fixture-eight-hostnames.png)
- [Fixture capture metadata](fixture-eight-hostnames.json)

This evidence-only run is excluded from all analyzed raw datasets. The image documents the fixed content's appearance; it does not establish native browser secure-DNS behavior or prove a numerical performance effect.

## Original data protection and collection sources

`original-data-sha256.json` records hashes of the five retained original input files. The validator checks them before reproduction. This detects changes relative to the package's original inputs, not an externally certified collection timestamp.

The [19 November collection snapshot](collection-source-2026-11-19/README.md) retains the exact scripts used for that session, collection metadata and source checksums. The [page collection log](replication-page-collection.log) contains the genuine page output rows. Maintained collectors under `scripts/` also include later path and screenshot options; the snapshot separates those maintenance changes from collection provenance.

The [20 November collection snapshot](collection-source-2026-11-20/README.md) preserves the exact two executed scripts. The [follow-up events](../../data/control-2026-11-20/events.jsonl) record real start and finish times and socket readiness for each window. The [control analysis record](../control_analysis_plan.json) contains the frozen sign rule and hashes of its historical inputs.
