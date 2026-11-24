# Data dictionary and timing boundaries

All raw JSONL lines represent one attempt, a priming attempt, or a declared event. Times ending in `_ms` use milliseconds. Timestamp fields ending in `_utc` retain wall-clock UTC for chronology. Elapsed intervals come from monotonic clocks. The collector field called `elapsed_ms` changes interpretation with its treatment and start boundary.

| Field or key | Meaning |
|---|---|
| `provider`, `domain`, `window`, `rep`, `block_id` | Comparison keys within a run. A window index can be reused across runs. |
| `phase`, `valid`, `error` | Priming versus measured attempt, response validation status, and recorded failure. Failures remain in denominators. |
| `query_base64`, `response_base64` | Exact DNS wire bytes when available. The offline Python decoder independently checks ownership and response structure. |
| `elapsed_ms` | Elapsed client call through DNS validation. Historical fresh UDP includes implicit bind. Later fresh UDP includes explicit bind and the close call. Established DoH and prebound UDP start after their transport resources are ready. |
| `bind_ready_ms`, `transport_elapsed_ms`, `post_bind_elapsed_ms` | Fresh UDP time to socket readiness, UDP send-call boundary to receive callback, and send call through validation. These apply only where the collector records the corresponding stage. |
| `connection_preexisting`, `alpn`, `tls_session_reused`, `local_port`, `connection_query_number` | Evidence about state at measurement and reuse across queries. Ports are local transient socket numbers. |
| `sequence`, `position`, `repeat_index`, `flow_id`, `flow_index` | In the repeatability control, the protocol order in a four-attempt block, slot number, within-protocol occurrence and prepared flow identity. |
| `flow_condition` | The same prepared flow for both repeats (`repeat_flow`) or different prepared flows for the second occurrence (`distinct_flows`). |
| `planned_offset_ms`, `actual_start_monotonic_ms`, `start_lateness_ms` | Requested slot offset, measured query start and difference from the targeted start. Pair lag uses the two measured starts on the same process clock. |
| `plt_ms`, `navigation.responseEnd`, `navigation.loadEventEnd` | Historical Chrome fixture completion and two Navigation Timing boundaries. |
| `fixture.elapsed_ms`, gate `start_ms` and `release_ms` | Synthetic-delay fixture completion and route-handler times. Gate interval overlaps use the route clock. Fixture completion uses the browser clock. |

Same-mode differences use later minus earlier for signed values. Cross-mode differences always use DoH minus UDP. Magnitudes use absolute paired differences. The absolute value of a signed median and the median of paired absolute differences answer different questions. Repeatability summaries count pairs, cells and windows separately because several pairs can share one query attempt.

The [artifact guide](ARTIFACT_EVALUATION.md) links fields to the datasets and results. The [reproduction guide](REPRODUCIBILITY.md) identifies the collectors and analysis commands for each stage.
