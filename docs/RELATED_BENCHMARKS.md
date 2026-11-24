# Closest benchmarks and the questions this replication can answer

This comparison identifies prior methods that are directly relevant to the project's timing boundaries, temporal matching and browser scope. It distinguishes an established technique from the additional question asked with that technique. A new measurement on one host can be informative without establishing a new transport mechanism or a universal provider ranking. Section and page locators below refer to the linked author or conference PDF, whose page numbering can differ from the published proceedings.

## Six closest primary studies

### Böttger et al. (2019): transport behavior and persistent connections

**Exact fit.** Section 3, PDF pp. 3–4, uses a local CoreDNS fixture with fixed answers, controlled query arrivals and deliberately delayed responses to examine transport behavior. Section 4, pp. 4–5, compares UDP and persistent/nonpersistent DoH at Cloudflare and Google. Section 5, pp. 5–6, measures browser loading. Artificial delay, provider matching, multiplexing and setup amortization are therefore prior methods.

**Additional question here.** How much does this client's measured contrast change when the UDP socket lifecycle and timing boundary change? A separate browser fixture tests propagation through two specified resource dependencies. It does not discover serialization or reproduce their real-site evaluation. The meaningful addition is a measured sensitivity with retained execution state, rather than another claim that reuse matters. [Original paper and DOI](https://arxiv.org/pdf/1909.06192), [publication record](https://doi.org/10.1145/3355369.3355575).

### Hounsel et al. (2020): direct queries and native browser outcomes

**Exact fit.** Section 3.1.1, PDF p. 2, measures real websites using Firefox and HAR load timings. Section 3.1.2, pp. 2–3, uses getdns and libcurl for direct queries, including UDP and reusable HTTP/2 DoH. It also identifies problems with interpreting individual HAR DNS components. Section 3.2 describes vantage points and network conditions.

**Additional question here.** The local-content fixture removes changing response bodies and origin transfers to examine one dependency structure. This trades ecological coverage for a narrower controlled outcome. It cannot support conclusions about native browser resolver policy or normal website page-load changes. A direct query benchmark and a browser benchmark must remain separate estimands even when both contain DNS-related waiting. [Original paper](https://arxiv.org/pdf/1907.08089), [publication record](https://doi.org/10.1145/3366423.3380139).

### Hounsel et al. (2021): repeated measurements and setup separation

**Exact fit.** Sections 2.1–2.2, PDF pp. 2–4, describe separate setup/query timing and different synchronous/asynchronous query behavior. Section 2.3, pp. 4–6, randomizes a hostname list, queries batches through resolver/protocol combinations and checks cross-traffic. The study measures home networks over a month. Repeated measurements, explicit connection costs and protocol scheduling differences are already recognized concerns.

**Additional question here.** A frozen estimate from one session is scored against selected later sessions. The repeatability control compares cross-protocol differences with same-protocol repeats at comparable short delays. The [repeatability results](REPEATABILITY_RESULTS.md) quantify those differences separately by run. The local results apply to one host. [Original paper](https://arxiv.org/pdf/2007.06812), [publication record](https://doi.org/10.1007/978-3-030-72582-2_26).

### Chhabra et al. (2021): default-client baselines and cache-miss control

**Exact fit.** Section 3.1, PDF p. 3, uses controlled names to induce cache misses. Section 3.4, p. 5, derives a reuse estimate under proxy constraints; Section 4.1, p. 6, validates its timing method against controlled nodes. Its baseline concerns default client resolution across countries. The limitations in Section 8 acknowledge proxy selection bias.

**Additional question here.** Direct UDP and pinned same-provider DoH isolate a different comparison. The project records actual session state and tests the sensitivity of a fixed local estimator. Repeated popular names do not reproduce controlled recursive misses, and one host cannot replicate worldwide deployment evidence. Same-provider matching should therefore be described as a targeted control, without suggesting it makes the two studies' populations or cache conditions equivalent. [Original paper](https://kumarde.com/papers/imc_doh.pdf), [publication record](https://doi.org/10.1145/3487552.3487849).

### Izhikevich et al. (2022): reusable UDP resources in ZDNS

**Exact fit.** Section 3.4, PDF p. 3, explicitly describes maintaining long-lived UDP sockets to avoid repeated creation and teardown in a high-throughput DNS scanner. Socket reuse is established implementation practice.

**Additional question here.** Its effect on a low-rate, per-query elapsed comparison needs to be measured in this instrument. A reusable socket changes more than allocation: its source port persists. Keeping several resources and recording which one handled each trial allows a sensitivity check on dependence on a single resource. It does not turn two sockets into a representative sample of Internet routes, nor supply a universal latency correction from the scanner's throughput results. [Original paper](https://faculty.cc.gatech.edu/~pearce/papers/zdns_imc_2022.pdf), [publication record](https://doi.org/10.1145/3517745.3561434).

### Lu et al. (2019): baseline constraints and repeated relative comparisons

**Exact fit.** Section 4.1, PDF pp. 7–8 (printed pp. 28–29), explains that TCP-only proxy support forces a DNS/TCP baseline. It compares protocol-specific medians of repeated queries from each retained proxy. Section 4.3, PDF p. 10, discusses reused and fresh connections.

**Additional question here.** Direct UDP avoids that particular baseline constraint, while the median of matched differences is a different summary from a difference of marginal medians. Neither choice establishes that adjacent queries share identical conditions. [Original paper](https://personal.utdallas.edu/~shao/papers/lu_imc19.pdf), [publication record](https://doi.org/10.1145/3355369.3355580).

## What the same-mode control measures

The completed historical and socket controls compare treatments inside matched provider/name/window/repetition blocks. Close timing reduces the opportunity for conditions to change, but does not remove that change. A signed DoH-minus-UDP difference mixes the protocols' client/service behavior with variability between their two observation times. An absolute paired difference is therefore an observed contrast, rather than an identified cryptographic penalty.

A same-mode control repeats UDP and repeats established DoH under the same declared timing policy. Its signed repeat differences reveal drift or order effects; its absolute repeat differences describe repeatability at the recorded separation. These are empirical reference quantities. They are not automatically a pure network jitter estimate, a lower bound on measurement noise, or a null distribution under which protocols are interchangeable. An earlier query may change cache state, and a connection can retain different service state from a datagram socket.

The extension uses two ready UDP sockets and two established HTTP/2 connections per provider and window. Each balanced block includes two UDP and two DoH requests. The six protocol orders and fixed start slots let the analysis compare observed pair lags. The audit verifies schedules, source ports, session identities, actual starts and all attempts. See the [frozen plan](REPEATABILITY_PLAN.md) and [run results](REPEATABILITY_RESULTS.md).

Using multiple resources addresses the possibility that one persistent socket or connection dominates a result. Flow-sensitive routing is a reason to inspect this sensitivity: transport ports can enter a router's flow identifier. Without route or service instrumentation, a flow-specific timing difference does not locate its cause. [Paris traceroute, Section 2.1, PDF pp. 1–2](https://conferences.sigcomm.org/imc/2006/papers/p15-augustin.pdf).

Cross-protocol and same-mode comparisons should use declared lag strata and preserve their block membership. Unequal separations make a simple comparison of pooled spreads hard to interpret. Four queries do not create four independent protocol replications, and multiple derived differences from the same block share observations. Statistical summaries should retain that dependence. Order balancing controls an order distribution; it does not ensure that every treatment sees the same instantaneous cache, route or queue.

The results show why magnitude needs a same-mode reference. In Cloudflare A1, the weighted median absolute cross-mode difference was 2.16 ms and the comparable same-flow DoH repeat difference was 2.50 ms. In the B1 hotspot run these medians were 6.95 and 9.89 ms. Check the full table for both providers, both flow conditions and the return run. Results describe the measured client, providers, names and periods. [Repeatability results](REPEATABILITY_RESULTS.md)

## Contribution language and browser boundaries

The study contributes a measurement audit that connects resource readiness, fixed-forecast transfer, within-mode query variation and delay propagation through a specified browser graph. Reuse, repeated observations and artificial waiting are established methods. These controls quantify what a single pooled contrast can hide in the recorded workload.

The browser experiments need distinct descriptions. The historical fixture waits for validated live DNS replies before releasing fixed local bytes. The delay-injection fixture changes requested waits and request dependencies; its delays are synthetic. Both omit native browser resolution and actual origin connections. Only the historical fixture measures live DNS. The newer fixture's recorded gate union describes overlapping timer intervals, not a packet trace or an exact decomposition of normal website load time.

A concise formulation is: “The historical browser fixture measures live-DNS waiting before fixed local content is released. A separate randomized experiment injects synthetic waits to test parallel and sequential resource dependencies. Both outcomes apply to the specified fixtures; native browser DNS and remote content delivery remain outside their scope.” The historical phase claim should identify both providers and layouts on 15 and 19 November, without implying that browser loads were collected on every later lookup date.

## Supplemental-only reference

Lu, C., Liu, B., Li, Z., Hao, S., Duan, H., Zhang, M., Leng, C., Liu, Y., Zhang, Z., & Wu, J. (2019). An end-to-end, large-scale measurement of DNS-over-encryption: How far have we come? In *Proceedings of the Internet Measurement Conference* (pp. 22–35). Association for Computing Machinery. [https://doi.org/10.1145/3355369.3355580](https://doi.org/10.1145/3355369.3355580)

The title, author order, year and DOI are present in the original paper. It uses the published proceedings pagination 22–35; its opening author-PDF page is unnumbered and later printed pages identify the proceedings sequence. This source supports the supplemental comparison above and is not added merely to increase the main paper's reference count.
