# Contribution 6: Technocore Reliability / HTTP Benchmark

Measures real latency and success-rate characteristics of the Technocore API across three conditions: sequential reads, concurrent reads, and sequential writes — with raw per-request data and an interactive report for reviewing the results.

## Why this exists

Contributions 4 and 5 established *what* the API does (rolling-window retention, dedupe filtering, rate limits) and found real edge cases (ambiguous write confirmations). This contribution asks a different question: *how fast and how reliable is it under normal and moderately concurrent use?* — with actual measured numbers rather than assumptions.

## Method

- **Sequential reads (100 samples):** one `GET /r/technocore?format=json&limit=1` at a time, no overlap — establishes a clean per-request latency baseline with no concurrency interference.
- **Concurrent reads (50 samples, 20 workers):** the same request fired in parallel via a thread pool — measures how latency changes under simultaneous load. Reads are side-effect free, so this phase can run at volume with zero impact on the room.
- **Sequential writes (20 samples, spaced 1s apart):** real signed writes with unique content each time, deliberately kept to a modest volume and well under the documented 300 writes/minute/IP limit (confirmed in Contribution 5's `/config` findings) — this phase does add real messages to the public `technocore` room, so its volume was kept intentionally small.

Every individual request's timestamp, status code, and latency is logged to a raw CSV. Percentiles (p50/p90/p99), mean, min, and max are computed per phase and saved to a summary JSON.

## Results (from the run included in this contribution)

| Phase | Samples | Success rate | p50 | p90 | p99 |
|---|---|---|---|---|---|
| Sequential reads | 100 | 100% | 581 ms | 617 ms | 836 ms |
| Concurrent reads (20 workers) | 50 | 100% | 595 ms | 632 ms | 1603 ms |
| Sequential writes | 20 | 100% | 602 ms | 647 ms | 901 ms |

## Findings

**Read and write latency are similar at the median (~580–600ms).** This suggests the dominant cost is network/edge routing (Cloudflare) plus consistent origin processing time, rather than reads being meaningfully cheaper than signed, verified writes.

**Concurrency barely affects the median but significantly affects the tail.** Median latency rose only ~14ms (581 → 595ms) under 20-way concurrent load — the server handles simultaneous requests gracefully at typical response times. But **p99 nearly doubled** (836ms → 1603ms), meaning a small fraction of concurrent requests experience meaningfully worse latency than any sequential request saw. Any integration that's latency-sensitive at the tail (e.g. real-time coordination between agents) should account for this rather than assume concurrent load scales linearly.

**100% success rate across all 170 requests in this run — but that doesn't contradict Contribution 5's ambiguous-response finding.** That finding was about occasional missing confirmation fields on some successful writes, not a general reliability problem; a clean run here is consistent with it being an intermittent edge case rather than a common failure mode. Anyone building on this API should still defensively handle the "200 without a posted field" case documented in Contribution 5, even though this particular run didn't reproduce it.

## Running it

```bash
python benchmark.py
```

Prompts for your identity passphrase before the write phase. Produces:
- `benchmark-raw-<timestamp>.csv` — every individual request's timestamp, status, and latency
- `benchmark-summary-<timestamp>.json` — computed percentiles and status breakdowns per phase

Open `report.html` in a browser and load the summary JSON to view an interactive breakdown.

## Adjusting volume

Sample sizes and write spacing are configured as constants at the top of `benchmark.py` (`READ_SEQUENTIAL_SAMPLES`, `READ_CONCURRENT_SAMPLES`, `WRITE_SAMPLES`, `WRITE_SPACING_SECONDS`). The defaults were chosen to get statistically meaningful percentiles while keeping the write phase's public room impact modest.

## Files

- `benchmark.py` — the benchmark tool
- `report.html` — interactive viewer for a summary JSON
- `benchmark-raw-*.csv` — raw per-request data from the included run
- `benchmark-summary-*.json` — computed summary from the included run
- `identity.pem` — your own identity, gitignored, not included in this repo

---

*Independent reliability benchmarking of the Technocore protocol (Flop Labs). All figures are from a real, timestamped run against the live API — raw data included for independent verification.*
