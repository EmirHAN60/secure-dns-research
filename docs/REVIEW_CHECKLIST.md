# Research questions and remaining validity limits

See the [artifact evaluation guide](ARTIFACT_EVALUATION.md) for the current claim-to-evidence index. This note records the earlier review criteria.

Review date: 22 November 2026. This checklist evaluates the completed 15, 19 and 20 November evidence described in the manuscript, together with the completed 22 November loopback and browser layout controls. The spaced public-resolver sessions are reviewed here as a design and reporting plan; incomplete session outcomes were not inspected. Their final interpretation requires the completed collection and audit.

## Questions, estimands and controls

| Research question | Quantity actually estimated | Control or evidence already available | Remaining issue after the proposed improvement |
| --- | --- | --- | --- |
| Does the UDP baseline change an established-DoH contrast? | Median paired client-and-service delay under fresh versus prebound UDP baselines | Randomized complete triplets, provider matching, recorded ports and separate timing stages in the completed 20 November control | Reused source ports can change service or path affinity. The baseline difference is not exclusively local socket cost. |
| How much local setup enters UDP timing? | Wall-clock duration of a specified creation/binding stage, plus a separately timed post-readiness operation | The same fresh UDP attempt has an explicit readiness boundary | Loopback removes public-network and resolver variation, but retains client/server scheduling, runtime and kernel work. It cannot turn elapsed time into processor cycles or explain all public-resolver differences. |
| Does a pooled direction transfer to another time period? | Accuracy of a fixed sign rule and error in predicting observed window medians | Retrospective historical holdouts and a locally frozen rule for the completed follow-up | Longer spacing and additional dates broaden the observed contexts. They do not create independent, representative draws from networks or users. Instrument/build changes must remain identified. |
| Are reversals large enough to matter under a chosen criterion? | Counts or error summaries after applying explicit absolute-delay thresholds | The existing evidence retains unrounded paired effects and complete windows | A threshold grid is descriptive sensitivity unless externally justified. Values inside a band do not establish statistical equivalence, perceptual insignificance or a universal acceptable DNS penalty. |
| Where does lookup waiting affect the fixture? | Paired changes through document response end and from there to load-event end | Historical fixed-content browser measurements and a per-pair phase identity | A response-end split locates a timing change but does not trace every DNS gate or identify its overlap. Sequential/parallel delay injection can test the chosen dependency mechanism, not native-browser DNS or real-site performance. |

## Claims that remain conditional

The completed control demonstrates that baseline choice can change a small observed contrast; it does not establish a universal correction. Its reported local setup stage and public-resolver treatment difference are different estimands. Subtracting their medians does not identify a causal remainder, and differences of effect medians must not be relabeled as the median paired baseline shift.

The historical within-window intervals condition on the windows being retained. Their narrowness can coexist with changing window medians. New intervals need an explicit resampling unit: paired attempts for within-window uncertainty, intact hostname groups for domain sensitivity, or observed session/window groups for temporal sensitivity. A small number of time groups leaves population coverage uncertain. The dependence warning follows the general principles of [Field and Welsh](https://doi.org/10.1111/j.1467-9868.2007.00593.x); that paper does not validate this exact estimator or forecast.

The prospective sign check evaluates a locally fixed rule, rather than an externally preregistered probability forecast. The historical leave-one-window-out calculation is retrospective. Training and scoring must retain their exact targets, including the UDP implementation, deadband convention, failures and ties. Repeating the historical fitting process after observing new windows would change the forecast being evaluated.

## Conditions for a stronger final claim

- Completed new sessions have actual start/end times, spacing, session IDs, software metadata and all attempts. Scheduled spacing is distinguished from observed spacing. Measurement workloads that run concurrently are disclosed.
- Loopback calibration states its packet path, readiness event, timer endpoints and server behavior. It remains a standalone instrument experiment rather than a substitute for the public-resolver comparison.
- Threshold results include the full declared grid and distinguish positive, negative and within-band outcomes. Neither the grid nor a preferred threshold is selected to remove inconvenient reversals.
- Any new browser control uses identical bytes across treatments, randomized paired blocks, recorded gate intervals and a clear completion definition. Artificial delay treatments are explicitly identified as synthetic. Such data are not counted as additional live-DNS measurements.
- The final abstract and conclusion distinguish observations from interpretation. They report effect magnitudes alongside sign counts and avoid claiming that additional dates remove cache, routing or client confounding.

## Contribution and limits relative to the literature

Persistent encrypted connections and separate application outcomes are established in the work of Hounsel and colleagues and Chhabra and colleagues. [ZDNS](https://doi.org/10.1145/3517745.3561434) already uses UDP socket reuse as an optimization; its throughput evidence does not provide this project's latency correction. The contribution is the measured sensitivity of this instrument and the observed transfer of a defined rule, supported by inspectable controls.

[Le Louët and colleagues](https://doi.org/10.52953/NUXL5710) measured resolver resource costs separately. This project still lacks processor counters, CPU utilization and energy measurements. Its architectural relevance is the lifecycle and protocol work being timed, not a quantified cost of cryptography. Controlled browser evidence also leaves native resolver policy, returned-address selection, origin TLS, CDN transfer and dynamic website behavior outside the estimand. Stronger local controls improve interpretation within that scope; they do not remove those boundaries.

## Completed local-control audit

The loopback analysis accepted 400 measured pairs and reported no failed attempts, including warmups. The median fresh readiness stage was 0.04585 ms. The median paired fresh-minus-prebound difference was +0.07750 ms for the whole call and +0.01920 ms for the ready query stage. These are separate summaries. Their marginal medians cannot be subtracted to identify an exact residual mechanism. The harness runs its responder in the same process and measures elapsed time, including scheduling and packet handling. It is a useful instrument calibration, rather than an estimate of cryptographic work or a correction for the public resolver results.

The [browser layout supplement](BROWSER_LAYOUT.md) contains 80 successful navigations in 20 randomized four-condition blocks. Independent audits verified the scheduled order, source snapshots, fixed payload hashes, seven image completions, request sequencing and concurrent waiting-gate counts. All sequential pages had one waiting gate at a time; parallel pages reached seven. The paired completion effects were +26.20 ms for parallel requests and +210.90 ms for sequential requests. The within-block interaction was +186.95 ms. This supports the dependence mechanism in the specified fixture under synthetic timing treatments.

The requested wait changed from 25 to 50 ms; the realized median waits changed from 30.59 to 58.68 ms for parallel pages and from 28.21 to 59.21 ms for sequential pages. Thus a nominal 25 ms increment is an assignment, not an exact realized elapsed increment. The graph-only increments of 25 and 175 ms are idealized comparisons. Timer and event-loop scheduling remain part of the measured treatment response, and the pooled gate medians provide descriptive context rather than a causal decomposition. Bootstrap intervals condition on this run, host and fixture.

## Final manuscript wording checks

- Table 3 should label the trial-magnitude column as the median of absolute paired differences, with its paired denominator. This differs from the absolute value of the signed session median. The threshold column concerns individual pairs, while forecast categories concern session medians.
- The main text should report a median paired completion change for the browser control. Calling it a change in the marginal median would describe a different statistic. The injected wait should be described as a requested target.
- The fixed calibration forecast is fitted from a longer historical session than each new three-window session. The target is an observed session median under a different amount of temporal coverage. This belongs among the transport limits, alongside date and time of day.
- A comparison with a zero-adjustment prediction measures forecast performance in the observed held-out sessions. With only three selected sessions, any improvement or deterioration remains a descriptive result, without a population accuracy guarantee.
- The public-resolver and local browser runs should retain separate counts and actual execution times. The local browser completed between public sessions; its 80 observations are not live-DNS attempts.
