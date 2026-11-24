# Revisions

## Version 1.2.0

- Added remote same-protocol repeats and cross-protocol comparisons with matched start intervals and multiple prepared client flows.
- Hardened both DNS parsers to validate A-record ownership through the answer CNAME chain. Added reproducible regression cases for unrelated answers and overlapping seeded window streams.
- Audited the schedules of the archived sessions and preserved the original code and records. Current collectors hash the experiment label, seed and window together.
- Added a reviewer evidence map, a comparison of primary benchmarks, citation metadata and a frozen evidence archive.

## 23 November 2026

- Applied the original frozen calibration to a separately planned session on another date. Retained the 22 November three-session analysis and scored the additional date separately.

## 22 November 2026

- Added held-out sessions with a fixed 20 November calibration and prespecified sensitivity bands at 0.5, 1, 2 and 5 ms. Retained each session, runtime metadata and its measured attempts.
- Added a deterministic IPv4 loopback UDP calibration with 400 randomized matched pairs.
- Added a fixed-content Chrome experiment with 80 navigations, identical delay treatments and sequential versus parallel resource dependencies.
- Rebuilt the paper around baseline sensitivity, transfer between sessions and controlled browser workload scope.

## 20 November 2026

- Added a randomized follow-up comparing disposable and prebound UDP sockets with established HTTP/2 DoH. The measurement records the time through explicit UDP binding and the query stage after socket readiness.
- Added six-window sensitivity analysis, retrospective sign checks and a fixed sign prediction scored on the new collection.
- Reframed the paper title around lookup latency and controlled browser loads. The browser analysis splits the load event at document response end using the saved Navigation Timing entries.
- Related the UDP control and held-window design to prior latency studies and ZDNS. Updated the offline build and integrity checks to include the new data, source archive, tables and figures.
- Removed a Git status export that had been inadvertently committed at the repository root.

## 19 November 2026

### Research and evidence

- Added a separately analyzed 19 November replication: 1,800 measured DNS lookups and 360 controlled browser navigations. Combined recorded sample: 3,600 lookups and 720 navigations.
- Preserved all five original input hashes and all original primary numerical estimates and intervals.
- Retained changes in the direction of Google's established-session contrast across windows on both dates. Dates are not silently pooled.
- Added whole-domain bootstrap sensitivity, paired sign fractions, and window/domain omission checks without trimming valid observations.
- Expanded the bibliography from eight to eighteen claim-linked sources, including later DoQ/HTTP3 and resolver resource studies, with a source audit and explicit validity boundaries.
- Added fifteen data-derived scientific charts, each exported as PNG, PDF and SVG.
- Added genuine browser screenshots of the fixed fixture and an offline report of captured verification output, with metadata and source logs.

### Structure changes

| Previous path | Current path |
|---|---|
| `analyze.py` | `scripts/analyze.py` |
| `build_paper.py` | `scripts/build_paper.py` |
| `page-load.mjs` | `scripts/page-load.mjs` |
| `experiment/dns_client.mjs` | `scripts/dns_client.mjs` |
| `experiment/measure_dns.mjs` | `scripts/measure_dns.mjs` |
| `experiment/test_dns.mjs` | `tests/test_dns.mjs` |
| `experiment/test_live.mjs` | `tests/test_live.mjs` |
| `paper_source.md` | `docs/paper_source.md` |
| `LIMITATIONS.md`, `PROTOCOL.md`, `REFERENCES.md` | Corresponding files under `docs/` |

The generated manuscript and submission PDF remain at the repository root. Original raw files remain in `data/`, while the repeat session is a separate subdirectory. The existing ignored personal submission guide is excluded from the public manifest and release archive.

### Reproduction and checks

`python scripts/reproduce.py` now runs the offline saved-data pipeline. Local tests cover paired aggregation, failed observations, missing comparisons, wire validation, treatment consistency, CLI paths and manifest tampering. The run recorded eighteen passing Python tests plus passing Node wire tests. It checks links, collection snapshots, protected inputs and generated figures, then writes the SHA-256 manifest after closing the log.

The README's redundant preparation footer was removed. The paper retains the course-required AI-use declaration. The repository was prepared locally; no commit or remote upload is performed by the research scripts.
