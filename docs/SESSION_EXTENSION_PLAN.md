# Frozen same-evening session extension plan

Recorded 2026-11-22T20:05:21.900300+00:00 before any new session collection. This local record is not an external preregistration.

Three planned sessions begin on 22 November 2026 at 20:06, 20:18 and 20:30 UTC. Each has three windows 90 seconds apart, ten repetitions, ten domain names, two providers and three client treatments: 1,800 measured attempts and 180 priming records. Actual starts, completions, missing sessions and software/network metadata will be reported. This is a same-evening study, not multi-day sampling.

## Practical-threshold sensitivity

Report **all** thresholds: 0.5, 1, 2 and 5 milliseconds. These illustrative per-query sensitivity bands are not validated utility or equivalence limits. Categorize each signed median as below -tau, inside [-tau,+tau], or above +tau, with exact boundary values inside. A signed median inside a band does not establish equivalence or that individual paired differences are small. Report median absolute paired differences and threshold exceedance rates separately, with the observation/window/session denominator explicit.

## Comparisons

Primary: established DoH minus fresh UDP and established DoH minus bound UDP, using whole elapsed time. Secondary: fresh minus bound UDP using whole elapsed time, post-bind send-to-validated-response time and send-to-receipt time. Preserve timer boundaries, local lifecycle differences and the source-port/network/cache-affinity caveat.

## Frozen forecast and retrospective checks

The JSON records the four fixed provider/baseline point forecasts from the separate 20 November calibration. Apply their signed and threshold categories to **every** new session without updating them. Historical data is not pooled with new observations; code/runtime/OS differences restrict transport interpretation. The new sessions are held out from this calibration.

A separate retrospective leave-one-session-out check uses the equal-weight median of the other session medians. It reports sign/category agreement and absolute error versus a zero-adjustment predictor. It must never be described as an issued prospective forecast. Require three completed sessions with the same recorded build for the primary leave-session summary.

## Dependence, missingness and reporting

Show all session/window medians, ranges, IQRs, median absolute paired differences and sensitivity to leaving a session out. With only three selected sessions, report no population confidence/equivalence claim. Do not treat thousands of within-session queries as thousands of independent session replicates. Different source/runtime/OS builds remain separate.

Do not analyze outcome records of running sessions. List absent/running/failed sessions explicitly. Exclude structurally invalid completed sessions with reasons; preserve measured failures and incomplete successful-pair counts without imputation or replacement. No outlier trimming or adaptive choice of sessions or thresholds is allowed.

The JSON companion freezes scheduled paths, collection seeds, source hashes, calibration input hash and exact category/forecast rules.
