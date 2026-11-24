# Interpretation limits

## Historical 15 and 19 November measurements

1. One Windows host was sampled on 15 and 19 November 2026. Access medium, ISP, location, competing traffic and path changes were not characterized. Two dates do not provide representative longitudinal or network coverage.
2. Each date contains three direct-DNS windows beginning five minutes apart. These are short-term samples, not complete diurnal cycles. Page timestamps describe their separate windows. Node.js and Chrome versions differ between dates, so date differences are composite session contrasts.
3. Public recursive cache state is unknown. Direct queries bypass the OS stub cache; prewarming encourages reuse without proving hits. TTL values are diagnostic only. The study does not claim verified recursive cache misses.
4. Holding provider and pinned destination IP constant reduces, but cannot eliminate, backend, anycast, routing and cache differences between UDP and HTTPS services.
5. The direct DNS workload uses ten fixed names, IPv4 transport and A questions without EDNS. No TCP fallback, HTTP/3, IPv6, induced packet loss or congestion treatment is included.
6. Application latency includes library, socket and validation work as well as network waiting. Fresh TCP/TLS setup is included in direct fresh-DoH queries, without resumed TLS. No CPU counters, energy or microarchitectural effects were measured.
7. The browser experiment is a fixed DNS-gated fixture. Returned A addresses are not contacted. Browser native resolver behavior, content-server TLS, real content transfer, CDN selection and website changes are not measured.
8. One fresh DoH session is shared within each fresh page, whereas direct fresh lookups open a connection per query. These are deliberately different units and cannot be compared as identical workloads.
9. Load-event timing is neither visual completeness nor user interactivity. The fixed document and seven images define the stopping condition.
10. Bootstrap intervals condition on the observed windows and successful pairs. Correlated repeated domains and only three windows per date prevent strong population claims. Whole-domain resampling is a sensitivity check with ten clusters and does not remove temporal dependence. A pooled established-session result can hide changes of sign across windows. Thirty page loads per condition give an unstable tail percentile.
11. Failures remain in raw data and attempt counts. Successful-latency summaries are conditional on success. No failed attempt is imputed as a successful timeout-duration observation.

## Follow-up limits

The new socket control measures the elapsed time through explicit UDP binding and the paired change from fresh to prebound operation. The latter can include source-port affinity, path or service behavior changes. Neither comparison identifies pure CPU cost. The local stage timer includes event-loop waiting. Socket close initiation is timed in the fresh whole call, and asynchronous teardown can extend beyond that timer.

The ten new windows provide additional measurements in one short collection period on the same host. Nearby windows can share network, cache and service conditions. The held-window error and prospective sign count describe those samples and lack a population confidence interpretation. The prospective rule crosses two changes from the original setup: explicit UDP binding and a new Windows build. Differences across collection dates cannot isolate either.

The browser phase boundary comes from Navigation Timing and the two intervals include browser work. Requests can overlap parsing and each other. The saved gate durations lack a shared start and end timeline for each resource. The analysis therefore cannot recover exact per-resource overlap or estimate native website load times.

## 22 November extension

The 20 November afternoon calibration and the three 22 November evening sessions allow a cross-date forecast check under the same OS and runtime. The date, time of day and unobserved network state can change together. The three held-out sessions sample one evening on one host. The observer records selected local route properties. Public transit, recursive cache state and resolver front ends remain unobserved. The ten names form a fixed workload.

The effect bands are illustrative lookup scales. A session median near zero can coexist with many larger paired differences. Report both quantities, together with denominators and measured failures. The session forecast scores describe the observed holdout and do not support population confidence or equivalence claims.

The loopback study measures wall-clock socket readiness and exchange time through a local fixed responder. Public socket lifetimes change the local port distribution and can change affinity through NAT or resolver paths. The local calibration is a separate estimate. The browser dependency experiment uses actual Chrome timing under synthetic waits and reports its realized timer intervals. The measured changes apply to the local fixture and its dependency graph.

The additional check on 23 November used the original fixed forecast with a separate, locally recorded plan. It supplies one extra evening session on the same host. It adds a held-out date while leaving morning conditions, distinct client networks and resolver cache state outside this evaluation.

## Same-mode repeatability extension

Same-mode differences estimate observed query-to-query variation at matched positions and start intervals. A prepared connection, socket, cache entry or network path can remain shared. Multiple prepared flows add observed variation across distinct client connections and ports. They provide no identification of the physical resolver or Internet route.

Primary estimates condition on successful comparable starts within common cells. Earlier timeouts or slower queries can delay later slots. The archive retains all attempts, rejected pair reasons, all-lag sensitivity results and exact pair denominators. Multiple pairs from the same four-attempt block share measurements. The weighted shares are descriptive. They do not estimate a protocol’s causal probability of exceeding a latency threshold. No same-mode quantity is subtracted from cross-mode differences.

The sequence used home Wi-Fi, a user-confirmed phone hotspot and a return to home Wi-Fi. Recorded local route properties matched across the home observations. The exact initial Wi-Fi profile and the upstream paths are unknown. Access conditions and time can change together. See the [context record](evidence/repeatability-source-2026-11-23/context-clarification-2026-11-24.json).
