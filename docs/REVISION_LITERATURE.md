# Literature comparison and the value of the replication

The closest literature already establishes that HTTPS setup can be amortized, that resolver choice affects comparisons and that DNS latency does not determine page loading by itself. Reconfirming those points is useful for validation but does not, on its own, explain the research value of another local benchmark. The stronger question is how sensitive a reported DoH penalty is to the measurement definition and whether an estimate transfers to observations collected outside the window used to fit it. This supplement connects that question to primary sources and states the limits of the resulting contribution.

## Comparison with the closest studies

| Primary study | Relevant established work | Relationship to this revision |
| --- | --- | --- |
| Böttger et al. (2019), Sections 4–5 | Compares UDP and persistent/nonpersistent DoH through Cloudflare and Google; examines DNS costs and browser loading | Provider matching and connection reuse are established controls. The revision examines sensitivity to the UDP implementation and timer boundary in this particular instrument. |
| Hounsel et al. (2020), Sections 3.1–3.2 | Separates a direct lookup tool from native Firefox page-load measurement; uses UDP and HTTP/2 DoH with reuse | The controlled fixture answers a narrower dependency question. It cannot replace their native-browser evaluation. |
| Hounsel et al. (2021), Section 2.2 | Measures setup separately and removes establishment time from reported encrypted-query response times | Separating setup is established practice. The revision applies comparable ready-state boundaries to the UDP baseline and tests the effect on the estimated contrast. |
| Chhabra et al. (2021), Sections 3.1, 3.4 and 4.1 | Uses default client resolvers, controlled authoritative names and proxy-derived timing; estimates connection-reuse timing and validates it against controlled nodes | Direct recorded session state is a different local instrument. It does not reproduce the study's coverage, default-resolver estimand or cache-miss control. |
| Izhikevich et al. (2022), Section 3.4 | ZDNS reuses UDP sockets to remove per-lookup socket creation and teardown work in a high-throughput scanner | A connectionless protocol can still incur local socket-management work. A reusable UDP treatment is an established implementation choice; its effect on this low-rate latency comparison must be measured here. |

The specific source passages are available in the author versions of [Böttger et al.](https://arxiv.org/pdf/1909.06192), [Hounsel et al. 2020](https://arxiv.org/pdf/1907.08089), [Hounsel et al. 2021](https://link.springer.com/chapter/10.1007/978-3-030-72582-2_26), [Chhabra et al.](https://kumarde.com/papers/imc_doh.pdf) and [Izhikevich et al.](https://faculty.cc.gatech.edu/~pearce/papers/zdns_imc_2022.pdf).

Chhabra et al.'s reuse result needs a precise description. Section 3.4 derives an upper-bound estimate after removing identified setup components because their proxy closes connections. Section 4.1 checks that estimate against repeated queries on controlled nodes. The present local measurement records actual session conditions, but direct setup/query timing also appears in Hounsel's work. That difference supports an instrument comparison, not a first-measurement claim.

## UDP socket reuse and timing definitions

UDP has no transport handshake, but a client implementation still acquires local socket resources. ZDNS explicitly identifies socket reuse as an optimization. Its evidence concerns throughput under large-scale concurrency; it does not establish a millisecond correction for a sequential Windows benchmark. The Node.js documentation independently distinguishes socket creation from the state in which the socket can receive packets: the listening event follows explicit binding or the implicit binding triggered by the first send. This provides an observable implementation boundary for stage timing. [Node.js UDP socket documentation](https://nodejs.org/docs/latest-v24.x/api/dgram.html#event-listening).

In the original client, both UDP and DoH construct the DNS message before starting their elapsed timer. Query encoding is therefore excluded from both. The relevant asymmetry is the socket lifecycle: UDP creates a socket inside each timed operation, whereas an established DoH treatment uses resources prepared earlier. That comparison describes a particular client workload. A ready-socket comparison answers a related but different question.

For a fresh UDP query, let `t_start` precede socket creation, `t_ready` follow completed binding and `t_done` follow validation. The same reply supports three measurements:

- Total client elapsed time: `t_done − t_start`.
- Local setup stage: `t_ready − t_start`.
- Elapsed lookup after socket readiness: `t_done − t_ready`.

Because these timestamps belong to one attempt, their decomposition does not require comparing different network replies. The post-readiness quantity still includes client scheduling, sending, service/network waiting and validation. It is not a packet-level RTT or an encryption-only cost. A separate reusable-socket treatment tests the broader lifecycle choice across attempts; that comparison can also change source-port and service-path conditions, so it should not be interpreted as a pure local setup intervention.

The same distinction applies to DoH. A fresh connection's total interval includes establishment; an interval beginning after transport readiness answers a conditional query question. An already established session is another treatment, rather than a value inferred simply by subtracting an average handshake. All reported contrasts need to name their baseline and starting event.

## Added value through sensitivity and transfer

The revised analysis can contribute evidence at two levels. First, it tests whether the size or sign of the observed DoH contrast depends on a disposable or reusable UDP baseline and on inclusion of local setup. If the change is small, that result constrains one proposed explanation for the original difference. If it is material, it shows why a benchmark number requires an implementation-specific definition. Neither outcome establishes that the chosen lifecycle is universally representative of DNS clients.

Second, transferring an estimated overhead to another window is a prediction task. A simple test fits a provider- and treatment-specific paired difference using designated training observations, applies it to held-out observations and reports prediction error alongside a zero-adjustment baseline. This is more informative than merely listing medians because it evaluates a practical use of the benchmark: predicting a later lookup from an earlier measured penalty. Held-out windows must remain outside the fitting procedure, and all evaluated windows must be retained. Selecting only windows that show a reversal would weaken the claim.

The result remains conditional on the sampled names, client, providers and network. A few windows do not establish population transportability, and held-window error cannot identify its physical cause. Cache changes, service handling, routing and client variability remain possible explanations unless separately observed. Field and Welsh (2007) provide general reasons to respect dependence when resampling; they do not validate this particular prediction rule or establish that nearby windows are independent samples.

## Controlled browser evidence

Hounsel et al. (2020) use native browser loading and separately measured lookup response times. Their discussion of misleading HAR DNS components also shows why an application trace requires careful interpretation. A fixed-content browser fixture offers control over one dependency graph, but its returned DNS addresses are not contacted. It measures the delay propagation created by those gates, not ordinary remote website loading.

An empirical trace replay can add workload structure if the source trace and extraction rules are recorded. It preserves only the represented request relationships. Replacing response bodies or remote transfers with local fulfillment still excludes actual content-connection setup, CDN placement and native resolver scheduling. Sengupta et al. (2024) demonstrate why real DNS/content connection relationships matter; their QUIC coalescing results cannot be inferred from a DNS-gated replay. A replay should therefore be described as a controlled workload derived from a recorded trace, without relabeling it as native page-load impact.

## Proposed contribution statement

This replication evaluates the sensitivity and transfer of a measured DoH penalty. It compares matched socket-lifecycle treatments, decomposes local setup from the same UDP attempt, and tests whether an estimate fitted in one collection window predicts held-out observations. These checks explain how an apparently precise protocol comparison can depend on the instrument and sampling context. The controlled browser experiment separately examines delay propagation through a recorded dependency structure. The contribution is a reproducible measurement audit with conditional empirical findings, rather than a new transport, a universal performance ranking or a claim that connection reuse was previously unknown.

## Suggested introduction and discussion prose

Prior work establishes the importance of persistent encrypted connections and separate lookup and browser measurements (Böttger et al., 2019; Hounsel et al., 2020, 2021). UDP socket reuse is also an established optimization in DNS measurement tools (Izhikevich et al., 2022). Building on those results, this study asks how much the reported DoH penalty changes when the UDP baseline and timer boundary change, and how accurately an estimate transfers to held-out collection windows. These questions make the value of the replication measurable without claiming a new DNS mechanism.

The baseline controls test a specific interpretation of the observed difference. Matching resource readiness reduces a lifecycle mismatch, while the within-attempt decomposition identifies the local stage included in total UDP time. Neither removes all client or service differences. Held-window prediction then tests whether the resulting estimate is useful outside its fitting window. The conclusions should follow the size of those measured effects and prediction errors, including evidence that a proposed explanation has little influence.

## New reference and source verification

Izhikevich, L., Akiwate, G., Berger, B., Drakontaidis, S., Ascheman, A., Pearce, P., Adrian, D., & Durumeric, Z. (2022). ZDNS: A fast DNS toolkit for internet measurement. In *Proceedings of the 22nd ACM Internet Measurement Conference* (pp. 33–43). Association for Computing Machinery. [https://doi.org/10.1145/3517745.3561434](https://doi.org/10.1145/3517745.3561434)

The author-hosted paper verifies the title, eight-author order, year and DOI. Section 3.4, author PDF p. 3, contains the UDP socket-reuse discussion. Proceedings pagination is 33–43; the author PDF uses independent pagination. This is a peer-reviewed measurement-tool paper, not a direct DoH-versus-UDP latency calibration. The main-paper bibliography identifies the publication as 2022; the later arXiv upload date does not change that year.

The Node.js documentation is an implementation reference used here to identify the listening/binding boundary. It supplies API semantics, not an experimental estimate of setup overhead. All comparisons above use existing source findings to motivate the revision; no new measured effect is asserted in this supplement.
