# Component 6: Cost and Latency Note

## 1. Daily Workload & API Call Projections

In a typical engineering college department or academic block:
- **Daily Influx:** Approximately 40 to 60 booking requests per business day during regular semester periods, rising to ~100 requests/day during exam or hackathon seasons.
- **Base API Calls:** 1 API call per incoming request.
- **Retry Rate:** ~5% of requests require 1 retry due to formatting anomalies or network jitter.
- **Estimated API Calls per Day:**
  $$\text{Calls}_{\text{normal}} = 50 \times 1.05 \approx 53 \text{ calls/day}$$
  $$\text{Calls}_{\text{peak}} = 100 \times 1.05 = 105 \text{ calls/day}$$

---

## 2. Latency Analysis

Each request processes through two stages:
1. **LLM Extraction Stage (Network Bound):**
   - Model: Gemini 1.5 Flash / Llama-3.1-8b-Instant
   - Time to First Token (TTFT): ~250 ms – 400 ms
   - Output generation (~60 tokens of JSON): ~300 ms – 500 ms
   - **Average LLM API Latency:** **600 ms – 900 ms** per request.
   - Heuristic Fallback / Offline Mode Latency: **< 1.5 ms** per request.

2. **Deterministic Python Validation Stage (CPU Bound):**
   - Fact checks, datetime validation, CSV lookups, hash set lookups: **< 0.1 ms** per request.

3. **Total End-to-End Latency per Request:**
   - With Live LLM: ~0.7 to 1.0 second per request.
   - Batch of 50 daily requests completes in **~35 to 45 seconds** sequentially (or ~5 seconds with concurrency).

---

## 3. Estimated Cost Analysis

Based on current cloud API pricing tiers (e.g. Gemini 1.5 Flash):

### Token Breakdown per Request:
- **System Prompt (Input):** ~320 tokens
- **User Request (Input):** ~30 tokens
- **Total Input Tokens:** ~350 tokens per call
- **JSON Response (Output):** ~55 tokens per call

### Cost Calculations:
- **Gemini 1.5 Flash Pricing (Standard Tier):**
  - Input: $0.075 per 1,000,000 tokens
  - Output: $0.30 per 1,000,000 tokens
  - Free Tier: Up to 15 Requests Per Minute (RPM) free of charge.

- **Cost for 50 Requests/Day (Paid Tier):**
  - Input Cost: $50 \times 350 \times \frac{0.075}{10^6} = \$0.00131$
  - Output Cost: $50 \times 55 \times \frac{0.30}{10^6} = \$0.00082$
  - **Total Cost per Day:** **~\$0.0021 (a fraction of a cent per day)**
  - **Monthly Cost (30 days):** **~\$0.06 / month**

### Conclusion:
The tool operates comfortably within the provider's free-tier limits (under 15 RPM). Even under a fully paid billing tier, the total operational cost is negligible (< $0.10/month), making it exceptionally cost-effective and practical for institutional deployment.
