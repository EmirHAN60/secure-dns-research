# Reproduction and collection procedure

## Saved datasets

| Session | Raw input directory | Derived output directory | Collection seed |
|---|---|---|---:|
| 15 November 2026 | `data/` | `results/` | 20261115 |
| 19 November 2026 | `data/replication-2026-11-19/` | `results/replication-2026-11-19/` | 20261119 |
| 20 November 2026 | `data/control-2026-11-20/` | `results/control_analysis.json` and companion tables | 20261120 |
| 22 November 2026, prospective evening sessions | `data/external-2026-11-22/` | `results/session_extension/` | 20261122–20261124 |
| 22 November 2026, UDP loopback | `data/loopback-2026-11-22/` | `results/loopback_summary.json` | 20261122 |
| 22 November 2026, Chrome delay injection | `data/browser-layout-2026-11-22/` | `results/browser-layout-2026-11-22/` | 20261122 |
| 23 November 2026, additional held-out date | `data/verification-2026-11-23/` | `results/additional_date.json` | 20261125 |
| 23–24 November 2026, repeatability control | `data/repeatability-2026-11-23/` | `results/repeatability/` | 20261123 with run and window namespaces |

Each of the first two sessions contains 1,800 measured lookup attempts, 120 lookup priming records and 360 page attempts. Page DNS gates and primers are retained separately. The follow-up targets 6,000 measured lookup attempts and 600 priming records across ten windows. The historical pooled sign is used only for the documented sensitivity and prediction checks. Errors remain in the attempt counts.

The original five input files are protected by the SHA-256 ledger in `docs/evidence/original-data-sha256.json`. This ledger detects changes relative to the retained original inputs; it is not a third-party timestamp or independent proof of collection history.

## Dependencies

Python dependencies are pinned in `requirements.txt`: NumPy 2.3.5, ReportLab 4.4.9 and Matplotlib 3.10.7. The authoring runtime was Python 3.12.14. The browser library is Playwright 1.62.1, pinned by `package.json` and `package-lock.json`.

| Component | Original session | Repeat session |
|---|---|---|
| Node.js | 24.22.1 | 24.22.3 |
| OpenSSL | 3.5.9 | 3.5.9 |
| Chrome | 157.0.8103.51 | 157.0.8103.79 |
| Playwright | 1.62.1 | 1.62.1 |

The same host reports an AMD Ryzen 7 7700, sixteen logical processors and approximately 30.9 GiB RAM. Full recorded platform versions are in the data directories. Runtime and browser versions differ across sessions. Consequently, a date contrast is not an isolated causal effect of time. Network access technology, ISP, route and background traffic were not characterized.

## One-command offline reproduction

From the repository root, with a compatible Node.js on PATH:

```powershell
python -m pip install -r requirements.txt
python scripts/reproduce.py
```

After dependencies are installed, the second command is offline. It does not send DNS queries or open Internet pages. It checks protected inputs, runs local tests, reanalyzes each complete date, creates sensitivity tables and plots, builds the paper, checks package links and artifacts, captures command output and writes the integrity manifest.

If Node.js is not on PATH, pass its executable explicitly:

```powershell
python scripts/reproduce.py --node "C:/path/to/node.exe"
```

The pipeline stops on a failed command, incomplete collection, response/treatment audit mismatch, wrong design count or missing required artifact. It does not hide the failure and continue to a successful report. `--skip-paper` is available when rebuilding analysis and plots while retaining an existing PDF.

## Individual offline steps

```powershell
node tests/test_dns.mjs
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/analyze.py --dns data/dns_raw.jsonl --pages data/pages.jsonl --page-dns data/page-dns.jsonl --out results --strict
python scripts/analyze.py --dns data/replication-2026-11-19/dns_raw.jsonl --pages data/replication-2026-11-19/pages.jsonl --page-dns data/replication-2026-11-19/page-dns.jsonl --out results/replication-2026-11-19 --strict
python scripts/robustness.py
python scripts/plot_results.py
python scripts/control_analysis.py
python scripts/plot_control_analysis.py
python scripts/browser_phases.py
python scripts/analyze_loopback.py
python scripts/session_analysis.py
python scripts/plot_session_analysis.py
python scripts/analyze_additional_date.py
python scripts/audit_order_reuse.py
python scripts/repeatability_analysis.py --require-runs A1,B1,A2
python scripts/plot_repeatability.py
python scripts/analyze_browser_layout.py --doc docs/BROWSER_LAYOUT.md
python scripts/plot_browser_layout.py
python scripts/build_paper.py
python scripts/validate_package.py --ignore-manifest
```

The analysis uses a fixed bootstrap seed and 4,000 resamples. The primary interval resamples matched successful blocks within observed windows. Domain-cluster resampling is a secondary conditional sensitivity. Neither establishes population coverage across unobserved network conditions. No valid observations are trimmed or winsorized. Artificial arrays used by local tests are not research observations and are not exported into the datasets.

`results/summary.json` and its counterpart under the historical replication directory contain the original-date estimates. CSV files expose marginal, paired, window, domain and leave-one-window-out results. `robustness.json` adds sign fractions and whole-domain resampling. The [repeatability summary](../results/repeatability/summary.json) records weighted estimates, matching coverage and the audit for each run. See the [figure manifest](../figures/repeatability_figure_manifest.json) for the new PNG, PDF and SVG exports.

Generation timestamps, PDF metadata and the verification log can change between reproductions. Statistical values should reproduce for unchanged raw inputs, dependency versions and seeds. The manifest covers a particular completed build; after regenerating files, finish by generating a new manifest rather than expecting byte-identical timestamps.

The PDF builder uses Times New Roman when the four Windows font faces are available. On other systems it uses the Unicode DejaVu Serif faces installed with the pinned Matplotlib dependency. Line breaks and pagination can change with the font. Tables and numerical results are unchanged by font selection.

`.gitattributes` disables Git line-ending conversion for this artifact so that a Windows checkout does not change the bytes covered by the raw-data ledger and manifest. Keep that file with the repository when committing or cloning the release.

## Collect an independent replication

Internet collection needs outbound UDP port 53 and TCP port 443 to 1.1.1.1 and 8.8.8.8. The page collector also needs installed Google Chrome. The direct DNS client uses only Node.js built-ins. For the browser library:

```powershell
npm ci
```

Use fresh output directories. The following example starts a new direct-DNS collection without touching the distributed data:

```powershell
node scripts/measure_dns.mjs --out replication/new-session/dns --windows 3 --reps 10 --interval-seconds 300 --seed 20261119
```

Then collect page windows into a separate fresh directory:

```powershell
node scripts/page-load.mjs --window w1 --reps 10 --seed 20261119 --out replication/new-session/pages
node scripts/page-load.mjs --window w2 --reps 10 --seed 20261119 --out replication/new-session/pages
node scripts/page-load.mjs --window w3 --reps 10 --seed 20261119 --out replication/new-session/pages
```

Do not run the lookup and page collectors at the same time. Leave several minutes between page windows. The distributed second-date session serializes a lookup window followed by its page window; exact starts and completion records are retained with the collection snapshot. The lookup collector schedules windows five minutes apart. Page start spacing is described by actual timestamps, not assumed to be exactly five minutes.

The page output refuses duplicate window identifiers in the same directory. The DNS collector refuses an existing raw output file. Timeouts and unsuccessful replies are retained without retries. OS DNS settings and system caches are not changed.

To analyze a new session without replacing published results:

```powershell
python scripts/analyze.py --dns replication/new-session/dns/dns_raw.jsonl --pages replication/new-session/pages/pages.jsonl --page-dns replication/new-session/pages/page-dns.jsonl --out replication/new-session/results --expected-windows 3 --expected-reps 10 --strict
```

The paper builder targets the recorded measurements in the distributed artifact. To collect a separate socket-control comparison, choose a fresh destination outside the package.

```powershell
node scripts/measure_controls.mjs --out ../socket-control-repeat --windows 10 --reps 10 --interval-seconds 90 --seed 20261120
```

Use at most 65,536 total planned messages per process, including primers. The collector assigns unique 16-bit transaction IDs for the run. It records the exact source hashes and the actual window start times. See [the analysis plan](CONTROL_ANALYSIS_PLAN.md) and [follow-up results](CONTROL_RESULTS.md) for the comparison and forecast definitions.

See [the held-out session plan](SESSION_EXTENSION_PLAN.md) for the scheduled collection protocol and fixed calibration forecasts. An independent cross-day replication should freeze its local-time slots and code hashes first, hold the app and OS build fixed, retain actual rather than scheduled times, and run each session in a separate directory. Use an independently recorded network identifier when changing networks. Report missing or stopped sessions and preserve the actual measurements. The published plan and raw files document the three observed evening sessions.

The [repeatability plan](REPEATABILITY_PLAN.md) defines all six four-attempt orders, two prepared flows per protocol, start slots and matching rules. The [executed source and commands](evidence/repeatability-source-2026-11-23/README.md) reproduce that instrument. Use a distinct run label, a fresh directory and a new local plan for new observations. Preserve actual dates even when a study directory was named at registration.

## Browser fixture and timing fields

The fixture performs live DNS, validates A answers and waits before fulfilling fixed HTML/SVG bytes. Returned addresses are not contacted. New contexts block service workers. A page-local in-flight promise avoids duplicate queries per hostname.

- Direct fresh lookup `elapsed_ms` includes lazy connection establishment.
- Page fresh DoH explicitly opens a shared connection inside the navigation gate. `gate_ms` includes that setup; the nested client's `elapsed_ms` begins after it.
- Established page DoH primes the connection before navigation. The primer uses a hostname outside the fixture workload.
- `plt_ms` is the observed navigation `loadEventEnd - startTime`. It does not measure visual completeness or later lazy content.
- `responseEnd` splits the measured load event into two phases on the navigation clock. See [browser phase analysis](BROWSER_PHASES.md).
- The [layout and delay injection experiment](BROWSER_LAYOUT.md) uses fixed local bytes and programmed delays. Its primary metric is script start to verified completion of the seven images. Its source is `scripts/browser_layout.mjs`.
- Per-page query numbers, unchanged stored connection time, HTTP/2 and TLS-resumption flags check the intended treatment. No socket UUID was recorded, so these are implementation diagnostics rather than packet-capture proof.

## Execution images

`docs/evidence/offline-verification.png` is an actual screenshot of a locally rendered report containing captured verification output. `fixture-eight-hostnames.png` is an actual browser fixture capture from a separately labeled evidence run. The source HTML, text log and capture metadata remain available. No fabricated terminal rendering is presented as a terminal screenshot. Evidence-only runs do not enter the research sample.

## Changing author metadata or manuscript text

`profile.json` supplies identity and the evidence repository URL. `docs/paper_source.md` contains the manuscript source. `docs/references.json` contains the checked bibliography and claim locators. Rebuild with `python scripts/build_paper.py` after editing. Open the final PDF, check the repository link and independently verify the submitted interpretation.
