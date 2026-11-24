# UDP socket calibration on IPv4 loopback

The public-resolver experiment combines a client socket choice with the network path and resolver. A separate local experiment sends an IPv4 A question to a deterministic UDP responder on 127.0.0.1. The responder runs in the collector's Node.js process and returns a fixed DNS message containing 192.0.2.42. Client and server use ephemeral ports. The measurement writes no changes to the operating system's DNS configuration.

Each of 400 measured blocks contains one fresh and one prebound UDP attempt in randomized order. Twenty warmup blocks precede them. The fresh client creates and explicitly binds its socket inside the timer. A single prebound socket is reused. Each attempt measures the pre-query stage from call start to readiness, the interval from readiness through response validation, and the whole call through initiating close where applicable. The offline decoder independently checks the DNS identity, question, response structure and answer address against the retained wire bytes.

The median fresh setup time was **0.046 ms**. At the median over matched pairs, fresh minus prebound UDP was **+0.078 ms** for the whole call and **+0.019 ms** from readiness through validation. All 400 measured pairs completed. Exact values are available in the [analysis JSON](../results/loopback_summary.json). The [raw attempts](../data/loopback-2026-11-22/loopback_raw.jsonl) and [runtime metadata](../data/loopback-2026-11-22/loopback_environment.json) are included.

The result is a local wall-clock calibration with the process, kernel, parser and event loop all involved. The responder has fixed behavior and the loopback path has no remote router, anycast endpoint or recursive cache. The experiment helps bound the scale of socket handling in this fixture. It has a different timing path from public DNS and supplies no direct subtraction term or per-query CPU timing.

To reproduce the analysis:

```powershell
python scripts/analyze_loopback.py
```

To collect a new run, use a fresh path whose parent directory already exists:

```powershell
node scripts/measure_loopback.mjs ../loopback-repeat
python scripts/analyze_loopback.py --data ../loopback-repeat --out ../loopback-repeat/summary.json
```
