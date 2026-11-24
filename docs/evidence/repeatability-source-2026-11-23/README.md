# Matched-position repeatability source archive

The two JavaScript files are byte-exact copies of the collector and DNS module locked in [the source lock](../../REPEATABILITY_SOURCE_LOCK.json). The [local analysis plan](../../REPEATABILITY_PLAN.json) and source lock were recorded before the first study query. This is a local timestamped plan, not external preregistration.

| Executed source | SHA-256 |
|---|---|
| `measure_repeatability.mjs` | `15d4115ea5ba81e00c42ee0e58abe0a1ccaeba3ac1df1b73be050b5f499abe1b` |
| `dns_client.mjs` | `c2026c7d49654414b6c632b988c9dc9058ce899639bd8ffc98aa771c367dc35f` |

`capture.json` lists collected and uncollected run states. Each completed run has an immutable `A1-capture.json`, `B1-capture.json` or `A2-capture.json`, containing repository-relative hashes of that run's files and its independent audit. A missing optional run is never presumed collected. `SHA256SUMS.txt` covers the archive files.

The directory date identifies the frozen study. Actual collection dates and times are taken from each run's environment file and ledger. In particular, A1 was collected on 23 November and the user-confirmed B1 run began on 24 November. The files are not renamed or retimestamped to disguise that transition.

## Completed collection chronology

All three planned runs were actually collected. Access types below are the user's account; they do not establish an ISP or independent physical route. Times are UTC.

| Run | User-reported context | Actual collector start UTC | Actual collector finish UTC | Measured attempts | Priming attempts | Measured failures |
|---|---|---|---|---:|---:|---:|
| A1 | Home Wi-Fi | 2026-11-23T21:49:41.438Z | 2026-11-23T21:55:06.212Z | 2880 | 240 | 0 |
| B1 | Phone hotspot | 2026-11-24T10:20:41.146Z | 2026-11-24T10:26:09.123Z | 2880 | 240 | 0 |
| A2 | Home Wi-Fi return | 2026-11-24T10:34:31.097Z | 2026-11-24T10:39:55.891Z | 2880 | 240 | 1 |

The one A2 UDP timeout remains in the raw data and failure count; it was not retried or replaced.

## Experimental design

Each run uses three windows, twelve blocks per provider/domain/window, and four requests per block. The two providers are Cloudflare and Google; the ten names and timing boundaries are fixed in the plan. Each complete run contains 720 blocks, 2,880 measured attempts and 240 separately labelled priming attempts.

Before every window, each provider has two separately prepared unconnected UDP sockets and two established HTTP/2 sessions. Every prepared flow is primed with each domain. The six orders `UUDD`, `UDUD`, `UDDU`, `DUUD`, `DUDU` and `DDUU` occur once per provider/domain/window under each flow condition:

- `repeat_flow`: both occurrences of a protocol use the same prepared flow.
- `distinct_flows`: the second occurrence uses the other prepared flow of that protocol.

Distinct socket/session objects are not assumed statistically independent. Their source ports, identifiers and connection metadata are retained. First-flow selections balance three zero/three one assignments within each six-order cell. The complete block pool is shuffled with a SHA-256-derived stream whose namespace contains the actual run ID and window. A1, B1 and optional A2 therefore have separate deterministic streams without adding the window number to a master seed.

Attempts target block offsets 0, 100, 200 and 300 ms. The collector awaits an earlier reply or timeout before starting the next attempt and records actual starts, ends and lateness. Every attempt remains in the raw output, including failures and late starts. The collector applies no analysis lag filter. The frozen analysis compares eligible adjacent-position pairs with observed start lags of 75–125 ms across corresponding balanced-order cells; it does not claim every individual block contains every same-mode/cross-mode comparison at the same lag.

DNS query construction precedes the lookup timer. Both UDP sockets and DoH connections are ready before measurement. Recorded elapsed times include application response handling and validation. Same-mode differences can include network, resolver, scheduling and client-state variation. Cross-mode magnitude is not corrected by subtracting a same-mode jitter median, and this experiment does not isolate encryption CPU cost.

## Network context and timing

A1, B1 and A2 are user-confirmed condition labels. The user changes the access network; the collector changes no system DNS or network settings. B1 starts only after explicit switch confirmation, and A2 starts only after explicit return confirmation. No physical access type is inferred from those labels. Fixed order, elapsed time and the date transition prevent a causal network-effect claim. Every run is analyzed separately.

The user's [separately recorded clarification](context-clarification-2026-11-24.json) identifies A1 and A2 as home Wi-Fi and B1 as a phone hotspot. A2 began on 24 November only after explicit confirmation of return to the original home access. Opaque local configuration observations matched A2 to A1 and differed from B1; B1's before/after observations matched each other. These observations do not identify an ISP or verify a cellular upstream or independent physical route. Personal network names are omitted. The clarification supersedes earlier uncertainty without changing the frozen plan, measured bytes or existing exact run ledgers.

Privacy-limited network observations contain media type and opaque local configuration tags, with no network names, private addresses, MAC addresses or published key. They cannot certify public egress or an unchanged physical route. A1 has a pre-run observation, but no contemporaneous post-run observation was captured; no next-day observation is substituted for it. Other runs list the observations actually collected.

## Collector arguments

The protocol arguments for A1 were:

```text
node scripts/measure_repeatability.mjs --session-id A1 --out data/repeatability-2026-11-23/A1 --windows 3 --reps 12 --interval-seconds 120 --step-ms 100 --seed 20261123 --plan docs/REPEATABILITY_PLAN.json --plan-sha256 e6e65ce182495677d9b4cd73a123f8c85bf86f75c4db915af17f81302c5bacde
```

B1 began on 24 November after the user explicitly confirmed the second access network. Its exact command was:

```text
node scripts/measure_repeatability.mjs --session-id B1 --out data/repeatability-2026-11-23/B1 --windows 3 --reps 12 --interval-seconds 120 --step-ms 100 --seed 20261123 --plan docs/REPEATABILITY_PLAN.json --plan-sha256 e6e65ce182495677d9b4cd73a123f8c85bf86f75c4db915af17f81302c5bacde
```

A2 began after explicit return confirmation with the following command:

```text
node scripts/measure_repeatability.mjs --session-id A2 --out data/repeatability-2026-11-23/A2 --windows 3 --reps 12 --interval-seconds 120 --step-ms 100 --seed 20261123 --plan docs/REPEATABILITY_PLAN.json --plan-sha256 e6e65ce182495677d9b4cd73a123f8c85bf86f75c4db915af17f81302c5bacde
```

Recorded directories must not be overwritten. A future independent collection needs a new truthful context, fresh output and a locally fixed analysis plan; running these historical commands cannot recreate historical network conditions.
