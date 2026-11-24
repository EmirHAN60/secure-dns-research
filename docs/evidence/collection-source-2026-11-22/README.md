# November 22 spaced-session source archive

This directory retains the exact maintained collector and DNS module used for three predeclared evening sessions on one host. The [frozen plan](../../SESSION_EXTENSION_PLAN.json) was recorded at 20:05:21.900300 UTC before the first collector started at 20:06:20.451 UTC. The [capture ledger](capture.json) records actual completion times, source hashes and repository-relative data-file hashes.

| Session | Target start UTC | Seed | Windows | Repetitions per name/provider |
|---|---|---:|---:|---:|
| session-01 | 2026-11-22 20:06 | 20261122 | 3 | 10 |
| session-02 | 2026-11-22 20:18 | 20261123 | 3 | 10 |
| session-03 | 2026-11-22 20:30 | 20261124 | 3 | 10 |

Targets are twelve minutes apart. Within each session, window targets are ninety seconds apart. Actual starts can differ because authorization, local observations and process startup take time. The ledger and raw event files preserve those differences. The sessions run serially without overlapping experiment traffic. No task scheduler, recurring automation or system network change was used.

Each complete session contains 1,800 measured attempts and 180 separately labelled priming attempts. The collector retains failures without retries or imputation. The frozen forecasts treat all three new sessions as held out; the November 20 study is historical calibration. The new observations share one evening and one host and must not be described as independent days or a second physical network.

## Commands and protocol identity

The following commands show the exact collector arguments, executed from the repository root using the same Node.js runtime:

```text
node scripts/measure_controls.mjs --windows 3 --reps 10 --interval-seconds 90 --seed 20261122 --out data/external-2026-11-22/session-01
node scripts/measure_controls.mjs --windows 3 --reps 10 --interval-seconds 90 --seed 20261123 --out data/external-2026-11-22/session-02
node scripts/measure_controls.mjs --windows 3 --reps 10 --interval-seconds 90 --seed 20261124 --out data/external-2026-11-22/session-03
```

They were separated by real waiting time in the current task. Repeating these commands sequentially would not reproduce the spacing. To collect another study, use fresh output directories and a new truthful schedule. Do not overwrite the distributed data or relabel future measurements with historical timestamps.

The treatments are the unchanged `udp_fresh`, `udp_bound` and `doh_warm` controls. Fresh UDP explicitly creates and binds a socket within the whole-call timer; bound UDP retains one unconnected socket per provider/window; established DoH retains one primed HTTP/2 connection per provider/window. Query construction is outside timing. Whole-call, post-bind transport, validation and connection-state fields retain their recorded definitions from the November 20 control study.

The [generated source diff](protocol-diff-from-2026-11-20.patch) shows that the only collector change since the November 20 execution snapshot is the early guard against exceeding 65,536 unique DNS transaction IDs. The DNS supporting module is byte-identical. Source differences and matching runtime versions are documented evidence, not proof that network or resolver conditions match historical calibration.

## Privacy-limited network observations

`observe_external_network.ps1` is the exact local observer used around the sessions. It reads .NET interface information and selects a UDP route without sending application payload. It records media type, reported link rate, virtual-adapter hints and opaque configuration tags. Reported Wi-Fi link rate is not measured Internet throughput.

The tags use HMAC-SHA-256 over local adapter/routing configuration with a private random key retained outside the public repository. Network names, private interface IP addresses, MAC addresses and the key are not published. No public-IP lookup is performed. A matching tag describes matching observed local configuration only; it cannot establish unchanged public egress, DNS backend, Internet route or absence of VPN influence.

The first observation occurred during session 01 after its collector had started. Subsequent before/after observations have their own timestamps. `session_metadata.json` lists the corresponding files in each session directory. Observations do not alter DNS or network settings. A repeated observer run with a different private key produces different tags, so the tags are not global network identifiers.
