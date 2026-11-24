# November 20 control collection source

The two `.mjs` files in this directory are byte-for-byte copies of the source loaded for the November 20 public-DNS control study. Their SHA-256 values are recorded before collection in the dataset's [design](../../../data/control-2026-11-20/design.json) and [environment metadata](../../../data/control-2026-11-20/environment.json). The source snapshot separates the executed version from later maintained-code changes.

The actual command, run from the repository root with Node.js 24.22.3, was:

```text
node scripts/measure_controls.mjs --windows 10 --reps 10 --interval-seconds 90 --seed 20261120 --out data/control-2026-11-20
```

The collector writes `control_raw.jsonl`, `events.jsonl`, `design.json` and `environment.json`. It refuses to overwrite an existing raw dataset. The default design schedules ten windows ninety seconds apart, with two providers, ten domain names, ten measured repetitions and three treatments per matched block. That gives 6,000 measured attempts plus 600 separately labelled priming attempts. Actual event timestamps, completion status and failures remain in the metadata and raw records. A slow window can postpone the next scheduled start.

## Treatments and timing boundaries

| Treatment | Socket or session state | Whole-call timing |
|---|---|---|
| `udp_fresh` | A new unconnected UDP socket explicitly binds to an ephemeral port for every query | Includes creation, awaited binding, send/response handling, validation and the synchronous close call |
| `udp_bound` | One unconnected UDP socket is bound before queries and retained per provider/window | Excludes its initial bind and final close; retains the same source port |
| `doh_warm` | One primed, established HTTP/2 connection per provider/window | Excludes connection establishment; includes request/response handling and validation |

The historical UDP client called `send()` on a new socket and let Node bind implicitly. This control study explicitly awaits `bind(0)` before sending. It therefore examines a changed implementation of the same fresh-socket lifecycle; it is not an identical-estimator replication. The [prospective analysis plan](../../control_analysis_plan.json) records that distinction before the new outcomes are analyzed.

`elapsed_ms` uses a monotonic process clock and excludes DNS query construction. For both UDP treatments, `transport_elapsed_ms` is the duration from the post-bind `send()` call to the received-message callback. `post_bind_elapsed_ms` extends that interval through response validation. `pre_send_ms`, `send_callback_ms`, `receive_ms` and `bind_ready_ms` are offsets from whole-call timing start. `socket_create_ms`, `bind_wait_ms`, `validation_ms` and `close_call_ms` are durations. The close call is timed; asynchronous teardown completion is not awaited.

DoH phase fields record request creation, request-write completion, response headers, first body data, response end and validation. These are application/event-loop timestamps, not packet-capture transmission timestamps or isolated CPU costs. HTTP/2, TLS version, resumption status, connection properties and local source ports are retained. Private interface addresses are not recorded.

Fresh and bound UDP can encounter different flow hashes, NAT mappings, routes or resolver affinity because their source ports differ. A whole-call difference cannot be attributed entirely to socket CPU work. Remote resolver cache state remains unknown despite priming. The operating-system release also changed from the historical 10.0.26200 to 10.0.26300, as recorded in metadata.

## Run the archived version separately

With Node.js and permission for outbound UDP 53 and TCP 443, this command makes new observations using the archived source and a fresh output directory:

```text
node docs/evidence/collection-source-2026-11-20/measure_controls.mjs --windows 10 --reps 10 --interval-seconds 90 --seed 20261120 --out data/new-run/control
```

No npm dependencies, browser or global DNS changes are required. New observations will not recreate historical network conditions. The archived version assigns a distinct 16-bit transaction ID to every query; keep the total query count at or below 65,536. The recorded design uses only 6,600 IDs. After collection, the maintained collector added an early rejection of larger designs. That guard was not present in this frozen execution snapshot and does not change the recorded study.
