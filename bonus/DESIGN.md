# Bonus Design — Vietnamese E-Commerce Support Chatbot Flywheel

## The problem

Imagine a customer-support chatbot for a Vietnamese e-commerce platform (returns,
warranty, shipping policies). Agents answer in Vietnamese and English; users
paraphrase constantly — "Tôi mua widget 10 ngày trước, có đổi trả được không?"
vs the eval holdout "Can I return a widget I bought 10 days ago?". The product
already emits OpenTelemetry traces (Day 13); the pipeline must turn those traces
into (1) a golden eval set and (2) DPO preference pairs without training on what
we grade on.

**Who uses it:** ML engineers and policy analysts curating data; end users never
see the pipeline.

**Why it is hard:** Schema drift in trace attributes; PII in free-text prompts
(PDPL Law 91/2025); paraphrase-heavy Vietnamese; small team, no dedicated Kafka
cluster; bandwidth and GPU budget limited compared to US cloud defaults.

---

## Architecture sketch

```
  Zalo / web chat
        │
        ▼
  Support agent (instrumented, gen_ai.* spans)
        │
        ▼
  Bronze: raw trace JSON (append-only, S3/MinIO)
        │
        ├─► validate + quarantine (PII regex, empty output, tool errors)
        │
        ▼
  Silver: flattened spans (traces.py pattern)
        │
        ├─► eval golden set  (split='eval', human-reviewed)
        │
        ├─► DPO pairs (ok vs error, same intent)
        │         │
        │         ▼
        │   decontaminate: exact + fuzzy 13-gram Jaccard
        │         │
        │         ▼
        └─► preference_pairs.jsonl ──► Day 22 SFT/DPO

  Policy docs (PDF/Markdown, VI+EN)
        │
        ├─► vector chunks (simple lookup RAG)
        └─► KG triples (multi-hop: product → category → warehouse)
```

---

## Load-bearing decisions (5 questions)

### 1. Source & shape — what lands in Bronze?

**Decision:** Land raw trace JSON verbatim; flatten to Silver nightly.

**Tradeoff:** *Edit-on-ingest* (normalize prompts in Bronze) vs *immutable Bronze*
(rebuild Silver from raw). **Choose immutable Bronze.** Upstream SDK versions
change `gen_ai.*` attribute names; if we normalize early, we lose auditability
and cannot replay when dedup or decontamination logic improves. Cost: larger
Bronze storage — acceptable at our volume (~50k turns/day).

**Rejected:** Streaming flatten into Silver on every span — adds operational
complexity (Flink/Redpanda) before we have replay-tested batch logic.

### 2. Batch or streaming?

**Decision:** Nightly batch for dataset curation; real-time only for alerting
(quarantine spike, eval overlap rate).

**Tradeoff:** *Hourly micro-batch* vs *nightly batch*. **Choose nightly.** DPO
training runs weekly; eval refresh is manual. Freshness beyond T+1 does not
change model quality yet. Hourly would 24× our DuckDB/Spark job cost for no
consumer.

### 3. Contracts & quality — what gets quarantined?

**Decision:** Pandera-style gate on flattened spans: required `user_input`,
`trace_id`, valid `status`; regex quarantine for phone numbers and CMND/CCCD
patterns before any dataset export.

**Tradeoff:** *Block the whole trace* vs *quarantine offending spans*. **Choose
span-level quarantine** so one PII leak does not discard a whole successful
conversation. Page on-call when quarantine rate > 3× trailing 7-day median —
early signal of upstream drift or a prompt-injection wave.

### 4. Flywheel — how do we avoid eval leakage?

**Decision:** Two-layer decontamination: exact match (lab default) **plus**
character 13-gram Jaccard ≥ 0.35 against eval inputs (see `pipeline/fuzzy_decontam.py`).

**Tradeoff:** *Embedding similarity* (sentence-transformers) vs *character n-grams*.
**Choose n-grams first.** Zero download, runs on laptop, no GPU, deterministic in
CI. Vietnamese tokenizers are inconsistent; char n-grams catch paraphrases and
diacritic variants ("tra lai" vs "trả lại") without a model. Embedding similarity
is the upgrade path when n-grams false-positive on short prompts.

**Rejected:** Exact match only — our lab run kept 1/3 pairs but a paraphrased
duplicate would still leak; offline eval would lie (see `bonus/fuzzy_demo.py`).

### 5. Train/serve parity — where could the future leak?

**Decision:** User features (lifetime spend, return count) joined with DuckDB
`ASOF JOIN` at trace timestamp, never "latest value."

**Tradeoff:** *Precomputed feature store snapshot* vs *ASOF at export time*.
**Choose ASOF at export** for now — one DuckDB query, same logic as the lab.
At scale, migrate to Feast with point-in-time keys; the semantics must not change.

**Example:** `return_count_90d` must count returns **before** the chat started,
not including the return discussed in the current session.

### 6. Vietnamese context — PDPL, infra, language

**Decision:** Pseudonymize `user_id` in exported JSONL; keep raw IDs only in
encrypted Bronze with 30-day retention. Normalize Unicode NFC before n-gram
decontamination (composed vs decomposed accents).

**Tradeoff:** *Cloud GPU embedding* vs *on-prem CPU n-grams*. **Choose on-prem
CPU** — PDPL cross-border transfer scrutiny and intermittent VN↔SG latency
make a local batch job cheaper and easier to legal-review than streaming vectors
to a US API.

---

## What breaks at scale (brief)

At 100× trace volume, the first bottleneck is **small JSON files in Bronze**
(listing overhead), not CPU. Fix: partition by `date/hour` in object storage,
compact weekly. Human eval review does not scale — stratified sampling (5% of
`split='eval'` candidates) with analyst sign-off.

---

## Cost & operations

~80% of monthly cost is **analyst time reviewing eval candidates**, not compute.
Cut cost by auto-filtering traces where `status='ok'` and tool latency < p95,
not by skipping decontamination.

---

## Prototype

Run `python bonus/fuzzy_demo.py`. It shows exact decontamination keeping a
paraphrased prompt that fuzzy 13-gram matching correctly drops — the single
decision this bonus implements from the design above.
