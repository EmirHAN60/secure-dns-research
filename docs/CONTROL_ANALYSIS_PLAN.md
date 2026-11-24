# Frozen control-analysis plan

Recorded: 2026-11-20T12:14:25.117482+00:00. This local record was written before this analyst inspected follow-up control results. It is not an external preregistration or independent timestamp authority.

## Sign transport check

The historical Google established-DoH minus fresh-UDP pooled median is 6.444900 ms from 600 matched pairs in six windows across 15 and 19 November 2026. Four historical window medians are positive and two negative. This does not supply a probability of a positive future result.

The frozen forecast is positive for **each** new window's median paired `doh_warm elapsed_ms - udp_fresh elapsed_ms`. Follow-up fresh UDP includes explicit socket creation and bind inside the timer. The historical implicit-bind implementation differs, so this is a sign transport check, not validation of exactly the same estimator. Use every planned completed window, including zero or opposite signs, and report complete-pair counts and failures. No adaptive window selection or tuning follows observed outcomes.

## Additional control contrasts

1. Fresh UDP minus pre-bound reused UDP using whole `elapsed_ms`, where fresh includes creation/bind and reused excludes already completed setup.
2. The same paired UDP treatments using common post-bind `transport_elapsed_ms` (send call through response receipt), excluding validation from both.
3. Established DoH minus reused UDP using whole measured `elapsed_ms`, an observed client-and-service contrast.

Persistent source ports can change network or cache affinity. Neither the whole-call contrast nor the post-bind contrast alone identifies local CPU cost or pure cryptographic overhead. Keep historical and control estimands distinct.

## Historical sensitivity

Report the pooled median and a conditional within-window resampling interval with window sizes fixed, all window medians and their sign counts/range, the median of window medians with equal window weight, leave-one-window/date-out point checks and sign prediction. Historical held-out checks are retrospective. They do not prove forecasting validity or independent representative sampling.

The JSON companion records raw historical input SHA-256 checksums and exact forecast text.
