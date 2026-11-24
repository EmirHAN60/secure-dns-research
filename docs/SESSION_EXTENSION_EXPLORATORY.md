# Exploratory session diagnostics addendum

Recorded 2026-11-22T20:07:00.427297+00:00, after freezing the primary plan and before this analyst inspected any new session latency outcomes. The frozen primary plan is unchanged. These requested diagnostics are exploratory, not externally preregistered primary tests.

For each completed session/window/provider/treatment, describe whole-call latency and available post-bind timers with attempt/success counts, medians and IQRs.

For Google, retain each window's marginal medians for established DoH, fresh UDP and bound UDP. Compare the paired-effect median with the difference of marginal medians, naming them separately. Within each session, center window marginal medians on that session's median window marginal; report the descriptive Pearson correlation of centered DoH and UDP medians only within the same verified build group, with window/session counts and no p-values. Show all window points.

This readout can describe co-movement or disagreement under the sampled client/service conditions. It cannot locate routing, cache, resolver, CPU or packet-level mechanisms, prove independence, or establish population correlation. Few windows and repeated names remain limitations.
