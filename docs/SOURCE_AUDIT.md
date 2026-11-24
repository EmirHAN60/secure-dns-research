# Secure DNS source audit

This audit covers the twenty-reference main bibliography. The original eighteen were checked on 15 and 19 November; the 20 November revision added Izhikevich et al. (2022), with its source locator and claim limits in the [revision literature note](REVISION_LITERATURE.md). The 23 November revision adds Augustin et al. (2006). The [closest-benchmark comparison](RELATED_BENCHMARKS.md) also identifies one supplemental-only source. Page numbers refer to the identified author PDF unless explicitly described as printed publication pages. Protocol specifications establish mechanisms. Empirical papers establish findings within their own designs.

The set contains twelve empirical DNS or networking studies, five IETF RFCs, one W3C Working Draft, one statistical methods article and one expert methodological editorial. The editorial is explicitly not peer reviewed. None of these sources establishes the cause of this project’s observed differences between collection windows.

## Avoiding Traceroute Anomalies with Paris Traceroute

**Reference key:** `augustin2006`. **Year:** 2006. **Type:** Peer-reviewed conference paper. **DOI:** [10.1145/1177080.1177100](https://doi.org/10.1145/1177080.1177100).

**Evidence:** Section 2.1, conference PDF pp. 1–2, describes flow-sensitive routing. It motivates resource sensitivity checks, without identifying a cause of this experiment's timing changes. [Conference-hosted original](https://conferences.sigcomm.org/imc/2006/papers/p15-augustin.pdf).

**Metadata:** The accessible original verifies title, author order and venue/year. The DOI landing page returned HTTP 403; indexed metadata agrees with DOI and proceedings pp. 153–158.

## The Dagstuhl Beginners Guide to Reproducibility for Experimental Networking Research

**Reference key:** `bajpai2019`. **Year:** 2019. **Type:** Primary expert editorial and methodological guide; explicitly not peer reviewed.

**DOI:** [10.1145/3314212.3314217](https://doi.org/10.1145/3314212.3314217).

**Primary record:** [The Dagstuhl Beginners Guide to Reproducibility for Experimental Networking Research](https://doi.org/10.1145/3314212.3314217).
**Full text:** [Original or author-hosted document](https://netd.cs.tu-dresden.de/papers/bbfkp-dbgre-19.pdf).

**Evidence location:** Sections 2.1–2.4 and 3.3, printed pp. 25–28.

**Supported claim:** Operational Internet measurements require repeated observations, documented metadata, raw-data preservation, validated tooling and explicit time/vantage-point scope.

**Project relevance:** Supports machine-readable raw data, seeds, validation, timestamps and a repeatable analysis package.

**Boundary:** Code/data availability improves inspectability; it does not guarantee future Internet timings reproduce numerically. This is not a peer-reviewed empirical DNS study.

## The Future of DNS Privacy: A Comparison of DNS over QUIC and DNS over HTTP/3

**Reference key:** `bielefeld2026`. **Year:** 2026. **Type:** Peer-reviewed conference chapter.

**DOI:** [10.1007/978-3-032-18268-5_10](https://doi.org/10.1007/978-3-032-18268-5_10).

**Primary record:** [The Future of DNS Privacy: A Comparison of DNS over QUIC and DNS over HTTP/3](https://link.springer.com/chapter/10.1007/978-3-032-18268-5_10).
**Full text:** [Original or author-hosted document](https://hpi.de/fileadmin/user_upload/90_Research_Groups/bajpai/Publications/2026-pam-doq-doh3.pdf).

**Evidence location:** Section 3.1–3.4, author PDF pp. 10–12; Sections 4–6 and conclusion, pp. 16–23.

**Supported claim:** A current study combines resolver feature probing with browser experiments; performance depends on supported resumption/0-RTT behavior, and DNS delay does not necessarily become equivalent page-load delay.

**Project relevance:** Establishes current context for interpreting h2 without resumption as a specific treatment and for measuring application outcomes separately.

**Boundary:** Their DoQ/DoH3 and Firefox-proxy results are not interchangeable with our HTTP/2 local-content fixture.

**Metadata note:** Publisher first online 10 March 2026, LNCS 16477. Publisher spells Sassalla; the author manuscript byline spells Sasalla. The bibliography follows the publisher’s spelling and ververis’s preferred lowercase form.

## HTTP/3

**Reference key:** `rfc9114`. **Year:** 2022. **Type:** IETF Standards Track RFC.

**DOI:** [10.17487/RFC9114](https://doi.org/10.17487/RFC9114).

**Primary record:** [HTTP/3](https://www.rfc-editor.org/rfc/rfc9114.html).

**Evidence location:** Sections 1.1–1.2 and 3.2–3.3.

**Supported claim:** HTTP/3 maps HTTP onto QUIC, with transport and stream-delivery behavior distinct from TCP-based HTTP/2.

**Project relevance:** Explains why measured h2 DoH overhead cannot be extrapolated to DoH3.

**Boundary:** Dedicated DoQ and DoH over HTTP/3 remain different protocol mappings.

## An Empirical Study of the Cost of DNS-over-HTTPS

**Reference key:** `bottger2019`. **Year:** 2019. **Type:** Peer-reviewed conference paper.

**DOI:** [10.1145/3355369.3355575](https://doi.org/10.1145/3355369.3355575).

**Primary record:** [An Empirical Study of the Cost of DNS-over-HTTPS](https://doi.org/10.1145/3355369.3355575).
**Full text:** [Original or author-hosted document](https://arxiv.org/pdf/1909.06192).

**Evidence location:** Sections 4–5, author PDF pp. 4–6.

**Supported claim:** Persistent connections amortize setup overhead, while larger DNS costs need not translate directly to larger page-load costs.

**Project relevance:** Motivates separate fresh/established treatments and separate lookup versus browser outcomes.

**Boundary:** One university vantage point and historical software; its numerical effects are not predictions for this dataset.

**Metadata note:** Proceedings pp. 15–21 verified against authors' institutional publication records; full-text preprint uses its own PDF pagination.

## Measuring DNS-over-HTTPS Performance Around the World

**Reference key:** `chhabra2021`. **Year:** 2021. **Type:** Peer-reviewed conference paper.

**DOI:** [10.1145/3487552.3487849](https://doi.org/10.1145/3487552.3487849).

**Primary record:** [Measuring DNS-over-HTTPS Performance Around the World](https://doi.org/10.1145/3487552.3487849).
**Full text:** [Original or author-hosted document](https://kumarde.com/papers/imc_doh.pdf).

**Evidence location:** Sections 3.1 and 3.4, printed pp. 353 and 355; Section 5 terminology, p. 357; cache limitation in Section 7, p. 362.

**Supported claim:** The worldwide comparison uses clients' default resolver baseline, unique names under a controlled authoritative zone, and explicit connection-reuse distinctions.

**Project relevance:** Required anchor; we adapt the connection distinction while using fixed providers and openly unknown recursive-cache state.

**Boundary:** Our data do not replicate their worldwide coverage, cache-miss control or default-resolver estimand.

## Anycast Latency: How Many Sites Are Enough?

**Reference key:** `schmidt2017`. **Year:** 2017. **Type:** Peer-reviewed conference chapter.

**DOI:** [10.1007/978-3-319-54328-4_14](https://doi.org/10.1007/978-3-319-54328-4_14).

**Primary record:** [Anycast Latency: How Many Sites Are Enough?](https://link.springer.com/chapter/10.1007/978-3-319-54328-4_14).
**Full text:** [Original or author-hosted document](https://ant.isi.edu/~johnh/PAPERS/Schmidt17a.pdf).

**Evidence location:** Abstract and Section 1, author PDF pp. 1–2; publisher abstract.

**Supported claim:** An anycast IP is announced from multiple physical sites; routing policies affect client-to-site mapping and latency.

**Project relevance:** Pinning provider IP and SNI controls destination service identity, without proving identical physical site or backend cache.

**Boundary:** Their study concerns four root services. It does not demonstrate a route or site change in our recursive-resolver trials.

**Metadata note:** Publisher citation styles the family name de Oliveira Schmidt; author paper often abbreviates it Ricardo de O. Schmidt. The bibliography follows the publisher citation.

## Bootstrapping Clustered Data

**Reference key:** `field2007`. **Year:** 2007. **Type:** Peer-reviewed methodological journal article.

**DOI:** [10.1111/j.1467-9868.2007.00593.x](https://doi.org/10.1111/j.1467-9868.2007.00593.x).

**Primary record:** [Bootstrapping Clustered Data](https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-9868.2007.00593.x).
**Full text:** [Original or author-hosted document](https://bemlar.ism.ac.jp/zhuang/Refs/Refs/field2007jrssb.pdf).

**Evidence location:** Abstract and Section 1, pp. 369–371.

**Supported claim:** Bootstrap validity depends on the dependence structure and model used for clustered observations.

**Project relevance:** Motivates preserving matched blocks and qualifying conditional uncertainty estimates.

**Boundary:** Does not validate this exact median bootstrap or well-calibrated population inference from three short windows; those cautions are our methodological judgment.

## DNS Queries over HTTPS (DoH)

**Reference key:** `rfc8484`. **Year:** 2018. **Type:** IETF Standards Track RFC.

**DOI:** [10.17487/RFC8484](https://doi.org/10.17487/RFC8484).

**Primary record:** [DNS Queries over HTTPS (DoH)](https://www.rfc-editor.org/rfc/rfc8484).

**Evidence location:** Sections 4, 5.1–5.4 and 9.

**Supported claim:** DoH maps DNS messages to HTTP exchanges; HTTP/2 is recommended, HTTP and DNS caches interact, and transport security is distinct from DNSSEC.

**Project relevance:** Protocol definition, wire-format POST validation and precise privacy framing.

**Boundary:** DoH protects the client-resolver channel, not anonymity from the resolver; no privacy effectiveness was tested.

## Comparing the Effects of DNS, DoT, and DoH on Web Performance

**Reference key:** `hounsel2020`. **Year:** 2020. **Type:** Peer-reviewed conference paper.

**DOI:** [10.1145/3366423.3380139](https://doi.org/10.1145/3366423.3380139).

**Primary record:** [Comparing the Effects of DNS, DoT, and DoH on Web Performance](https://doi.org/10.1145/3366423.3380139).
**Full text:** [Original or author-hosted document](https://softsec.rub.de/files/pdf/www2020-dns-dot-doh.pdf).

**Evidence location:** Abstract; Sections 3.1–3.2 and 4.

**Supported claim:** DNS response-time rankings and browser page-load rankings can differ; network conditions and retransmission behavior matter.

**Project relevance:** Supports treating lookup latency and load-event time as separate outcomes, with actual browser measurement.

**Boundary:** Their native Firefox/global-cloud experiment is substantially broader than our intercepted-content fixture.

**Metadata note:** Author-hosted publication page and author CV verify final venue/year and pp. 562–572; preprint originated in 2019 but publication year is 2020.

## Can Encrypted DNS Be Fast?

**Reference key:** `hounsel2021`. **Year:** 2021. **Type:** Peer-reviewed conference chapter.

**DOI:** [10.1007/978-3-030-72582-2_26](https://doi.org/10.1007/978-3-030-72582-2_26).

**Primary record:** [Can Encrypted DNS Be Fast?](https://link.springer.com/chapter/10.1007/978-3-030-72582-2_26).
**Full text:** [Original or author-hosted document](https://kevin.borgolte.me/files/pdf/pam2021-can-encrypted-dns-be-fast.pdf).

**Evidence location:** Sections 2.1–2.3 and 3.1; publisher full text.

**Supported claim:** Connection setup and query response time are separate costs, and no resolver/protocol combination performs best for every measured client.

**Project relevance:** Motivates verified connection-state treatments and conditional, provider-specific interpretation.

**Boundary:** 2,693 analyzed US home-network devices; no browser page-load measurements. This does not establish our short-window sign changes' cause.

**Metadata note:** The final publisher count is 2,693; one author webpage has a discrepant older count.

## DNS over Dedicated QUIC Connections

**Reference key:** `rfc9250`. **Year:** 2022. **Type:** IETF Standards Track RFC.

**DOI:** [10.17487/RFC9250](https://doi.org/10.17487/RFC9250).

**Primary record:** [DNS over Dedicated QUIC Connections](https://www.rfc-editor.org/rfc/rfc9250.html).

**Evidence location:** Sections 3.2, 4.5 and 5.5.1.

**Supported claim:** DoQ is a dedicated DNS mapping over QUIC with resumption, 0-RTT and persistent-connection considerations.

**Project relevance:** Defines an unmeasured transport boundary and a concrete future comparison.

**Boundary:** A standards mechanism is not empirical proof of a universal speed advantage.

## DNS Privacy with Speed? Evaluating DNS over QUIC and Its Impact on Web Performance

**Reference key:** `kosek2022`. **Year:** 2022. **Type:** Peer-reviewed conference paper.

**DOI:** [10.1145/3517745.3561445](https://doi.org/10.1145/3517745.3561445).

**Primary record:** [DNS Privacy with Speed? Evaluating DNS over QUIC and Its Impact on Web Performance](https://doi.org/10.1145/3517745.3561445).
**Full text:** [Original or author-hosted document](https://vaibhavbajpai.com/documents/papers/proceedings/doq-imc-2022.pdf).

**Evidence location:** Sections 2–3.2, author PDF pp. 2–5; especially Section 3, p. 3.

**Supported claim:** Distributed measurements distinguish handshake from resolution time and evaluate DoQ against HTTP/2 DoH, with session resumption explicitly recorded.

**Project relevance:** Supports treating HTTP version, resumption and transport as experimental conditions, rather than a single generic encrypted-DNS cost.

**Boundary:** DoQ and resumed TLS are outside our non-resumed HTTP/2 treatments; their speedups are not observations from this project.

## Effects of Secured DNS Transport on Resolver Performance

**Reference key:** `lelouet2024`. **Year:** 2024. **Type:** Peer-reviewed journal article.

**DOI:** [10.52953/NUXL5710](https://doi.org/10.52953/NUXL5710).

**Primary record:** [Effects of Secured DNS Transport on Resolver Performance](https://www.itu.int/pub/S-JNL-VOL5.ISSUE1-2024-A04).
**Full text:** [Original or author-hosted document](https://www.itu.int/dms_pub/itu-s/opb/jnl/S-JNL-VOL5.ISSUE1-2024-A04-PDF-E.pdf).

**Evidence location:** Sections 4–5, particularly 5.1–5.5, printed pp. 50–58.

**Supported claim:** Resolver resource cost can be separated into connection establishment, connection upkeep and message processing; client connection behavior affects server load.

**Project relevance:** Provides the computer-architecture connection while showing that elapsed lookup latency is not a CPU-cycle, memory or energy measurement.

**Boundary:** Their controlled server benchmarks and throughput costs cannot be estimated from our client-side wall-clock delays.

**Metadata note:** ITU landing metadata and article byline print Ahmed Amaou, while the author biography on p. 61 prints Ahmed Amamou. The APA string preserves the published byline/metadata. The two spellings differ within the publication record.

## Domain Names—Implementation and Specification

**Reference key:** `rfc1035`. **Year:** 1987. **Type:** IETF Internet Standard RFC.

**DOI:** [10.17487/RFC1035](https://doi.org/10.17487/RFC1035).

**Primary record:** [Domain Names—Implementation and Specification](https://www.rfc-editor.org/rfc/rfc1035.html).

**Evidence location:** Sections 3.2.1, 4.1, 4.2.1 and 7.4.

**Supported claim:** DNS message structure, UDP port 53 transport and TTL-governed record caching are separately specified.

**Project relevance:** Basis for matching wire-format A queries and independently validating stored responses.

**Boundary:** Bypassing the OS resolver does not remove recursive caching; that is an inference from the separate cache layers.

## Cache Me If You Can: Effects of DNS Time-to-Live

**Reference key:** `moura2019`. **Year:** 2019. **Type:** Peer-reviewed conference paper.

**DOI:** [10.1145/3355369.3355568](https://doi.org/10.1145/3355369.3355568).

**Primary record:** [Cache Me If You Can: Effects of DNS Time-to-Live](https://doi.org/10.1145/3355369.3355568).
**Full text:** [Original or author-hosted document](https://ant.isi.edu/~hardaker/papers/2019-10-cache-me-ttls.pdf).

**Evidence location:** Introduction, printed p. 101; Sections 3–4, pp. 103–107.

**Supported claim:** TTL effects emerge from distributed caches, differing record sources and resolver behavior, and materially affect observed DNS latency.

**Project relevance:** Explains why direct queries and prewarming do not prove a globally fixed recursive-cache state; TTLs remain diagnostics.

**Boundary:** Cache expiration cannot be identified as the cause of this project’s time-window differences without authoritative or cache-hit evidence.

## On Cross-Layer Interactions of QUIC, Encrypted DNS and HTTP/3: Design, Evaluation, and Dataset

**Reference key:** `sengupta2024`. **Year:** 2024. **Type:** Peer-reviewed journal article.

**DOI:** [10.1109/TNSM.2024.3383787](https://doi.org/10.1109/TNSM.2024.3383787).

**Primary record:** [On Cross-Layer Interactions of QUIC, Encrypted DNS and HTTP/3: Design, Evaluation, and Dataset](https://doi.org/10.1109/TNSM.2024.3383787).
**Full text:** [Original or author-hosted document](https://vaibhavbajpai.com/documents/papers/proceedings/quic-tnsm-2024.pdf).

**Evidence location:** Abstract, Section I and Figure 1, author PDF pp. 1–2.

**Supported claim:** DNS and content-transport handshakes interact on the page-loading path; coalescing DoQ and HTTP/3 changes the setup structure.

**Project relevance:** Explains why a DNS-gated local-content fixture cannot estimate real content-transport, connection-coalescing or CDN effects.

**Boundary:** Their cross-layer gains are outside the properties measured by this HTTP/2-only fixture.

**Metadata note:** Final journal byline has five authors. Earlier arXiv metadata includes a different author list; the bibliography follows the final journal list. Publisher issue metadata verifies pp. 2992–3007.

## HTTP/2

**Reference key:** `rfc9113`. **Year:** 2022. **Type:** IETF Standards Track RFC.

**DOI:** [10.17487/RFC9113](https://doi.org/10.17487/RFC9113).

**Primary record:** [HTTP/2](https://www.rfc-editor.org/rfc/rfc9113.html).

**Evidence location:** Abstract; Sections 5 and 9.

**Supported claim:** HTTP/2 provides streams, field compression and connection management over TCP.

**Project relevance:** Basis for h2 negotiation and one shared connection across a page's concurrent hostname gates.

**Boundary:** Multiplexed streams do not make HTTP/2 equivalent to QUIC or eliminate all TCP-level blocking.

## Navigation Timing Level 2

**Reference key:** `navigation2026`. **Year:** 2026. **Type:** W3C Working Draft.

**DOI:** None assigned in the cited document.

**Primary record:** [Navigation Timing Level 2](https://www.w3.org/TR/2026/WD-navigation-timing-2-20261102/).

**Evidence location:** Sections 3.1 and 3.3.

**Supported claim:** A navigation entry starts at zero and its duration ends at loadEventEnd, after load-event handling.

**Project relevance:** Defines the fixture's browser metric precisely.

**Boundary:** A load event is not visual completeness, interactivity, or completion of all future lazy-loaded content.

## Interpretation safeguards

Published latency or page-load effects remain findings of the cited studies. The project’s own estimates come from its saved observations. Same-provider endpoints, prewarming and transport metadata reduce specific ambiguities without proving complete equivalence of routing, caches or implementations. The browser fixture measures DNS gating with intercepted content, while native browser resolution and remote content delivery remain outside its scope.

The statistical source motivates dependence-aware resampling but does not validate population inference from a few nearby windows. The reproducibility guide supports an inspectable artifact; it does not guarantee identical future timings on an operational network. The project is an introductory replication of established distinctions, without a first-study or new-protocol claim.
