# Arguments for a research discussion

This note records the reasoning for the 19 November version. The [revision literature comparison](REVISION_LITERATURE.md), [socket control results](CONTROL_RESULTS.md) and [browser phase analysis](BROWSER_PHASES.md) provide the updated evidence for the revised paper.

## A conditional overhead

A query that opens a TCP/TLS/HTTP2 connection differs from one sent over an established connection. Reporting one number without connection state combines workloads. Raw socket metadata and query sequence information make the treatments auditable. This follows existing literature; the contribution is its explicit application and verification in the present sample.

## A better defined baseline with remaining confounders

Comparing an ISP resolver with public DoH changes transport and infrastructure. Here each operator is its own baseline and the address is pinned. This reduces one explanation for a difference. It does not identify encryption's pure causal cost: anycast sites, caches, front ends, socket handling and service configuration can differ. The defensible outcome is an observed client-and-service contrast under recorded conditions.

## Narrow pooled intervals and unstable windows

Google's original established-session contrast is positive when pooled but changes sign across windows. Resampling within those windows does not generate independent new network conditions. Domain-cluster resampling preserves repeated observations within names but does not solve time dependence. Showing this sign change is more informative than presenting one precise pooled estimate as permanent behavior.

## A second date without a population claim

The 19 November session repeats the workload with a new seed and separately recorded software metadata. Its results are not silently pooled with the original. Agreement supports repeatability under the sampled conditions. Disagreement cannot identify whether routing, caching, load or software context caused it. Neither outcome establishes all-day or international behavior.

## Resource counts versus the DNS critical path

The fixture's main-document lookup blocks parsing. Later distinct-name lookups can overlap on a shared connection. The one-hostname layout memoizes one resolution despite seven images. Multiplying a query difference by the image count therefore describes a different graph. The load event supplies an observed browser outcome while content remains fixed.

## A deliberate browser boundary

Returned DNS addresses are not contacted. Fixed bytes remove CDN selection, site TLS and changing content, which helps inspect DNS gating. They also exclude native caching, prefetching, address racing and fallback. The results cannot rank Chrome's native DoH implementation or general website performance. Native-browser resolution with network traces would be a separate experiment.

## Architecture relevance

Protocol layers introduce possible parsing, encryption and connection-management work. Application elapsed time also contains network waiting. It does not directly measure CPU cycles or energy. Studies of resolver CPU/memory and QUIC transports are useful comparisons because they test other layers; their results cannot be transferred into these samples.

## Supporting evidence

- Immutable query and response bytes, with priming and all attempts retained.
- Independent wire decoding and connection-treatment checks.
- Matched contrasts rather than subtraction of unrelated averages.
- Window/domain tables, sign fractions and alternative resampling units.
- Separate collection-date metadata and summaries.
- Data-derived plots, local tests and captured execution output.
- An offline reproduction command.

Defend this as a transparent introductory replication. It does not establish a first-ever method, a new protocol, the cause of a sign reversal or a worldwide best resolver.
