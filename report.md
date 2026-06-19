# Lab Report — Day 17: Data Pipeline Engineering (Track 2)

| Field | Value |
|---|---|
| **Full name** | Võ Thanh Hiệp |
| **ID** | 2A202600836 |
| **Course** | Track 2 — AI Engineering |
| **Lab** | Day 17 — Data Pipeline Engineering |
| **Repository** | `2A202600836-VoThanhHiep-Day17` |

---

## 1. Executive summary

This lab implements a runnable, zero-key data pipeline for AI workloads on DuckDB
and pure Python. The pipeline covers the full **Medallion ETL** path (Bronze →
Silver → Gold), quality gates with quarantine, a pure-Python DAG orchestrator,
idempotent streaming, and the **agent-data flywheel** that turns production agent
traces into eval and DPO training datasets. A optional **dbt** track and a **bonus
design + prototype** extend the lab toward real-world Vietnamese e-commerce
support scenarios.

All core verification checks pass: **`verify.py` 16/16**, **`pytest` 18/18**,
and **`dbt build` PASS=11**.

---

## 2. Objectives

The lab targets three interconnected goals from the course deck:

1. **Medallion pipeline with quality gates** — ingest raw orders, validate and
   quarantine bad records, deduplicate in Silver, aggregate completed orders in Gold.
2. **Agent-data flywheel** — flatten OpenTelemetry `gen_ai.*` span trees into
   Bronze, curate eval and DPO preference pairs, decontaminate against eval leakage,
   and build point-in-time features with `ASOF JOIN`.
3. **Complex retrieval** — compare knowledge-graph multi-hop traversal against
   flat vector chunk retrieval for questions that require joining facts across
   documents.

---

## 3. Implementation overview

### 3.1 Medallion ETL (T1–T3)

| Stage | Module | Behavior |
|---|---|---|
| Extract | `pipeline/extract.py` | Load all raw rows into Bronze (append-only) |
| Validate | `pipeline/validate.py` | Pandera schema gate; bad rows → `quarantine.csv` |
| Transform | `pipeline/transform.py` | Silver dedup on `order_id`; Gold daily aggregates |
| Orchestrate | `pipeline/dag.py`, `main.py` | Topological DAG execution |

**Results on seed data:**

- 13 Bronze rows ingested (16 raw including duplicates and bad records after gate)
- 5 duplicate rows dropped in Silver
- 3 bad records quarantined (null `user_id`, negative `amount`, invalid `status`)
- 5 Gold daily rows (completed orders only)
- 0 duplicate `order_id` remaining in Silver

### 3.2 Orchestration & streaming (T2, T5)

- **`pipeline/dag.py`** — lightweight DAG runner respecting task dependencies.
- **`pipeline/streaming.py`** — partition-by-key topic with idempotent consumer
  (duplicate `event_id` ignored on replay).

### 3.3 Agent-data flywheel (T6–T8)

| Step | Module | Output |
|---|---|---|
| Trace → Bronze | `pipeline/traces.py` | 21 flat span rows from 8 traces |
| Eval curation | `pipeline/dataset.py` | 2 golden eval rows (`split='eval'`) |
| DPO pairs | `pipeline/dataset.py` | 3 raw pairs → 1 clean pair after decontamination |
| Point-in-time | `pipeline/features.py` | ASOF join vs naive leaky join (2 leaked rows) |

Generated artifacts (via `flywheel.py`):

- `datasets/eval_golden.jsonl`
- `datasets/preference_pairs.jsonl`

### 3.4 Knowledge graph & RAG (Bonus core)

- **`pipeline/embed.py`** — doc → recursive chunk → hash embedding (zero-key).
- **`pipeline/kg.py`**, **`kg_demo.py`** — triple extraction, 2-hop traversal
  (widget → accessory → Hanoi), vector foil showing split facts across chunks.

### 3.5 dbt track (optional)

- **`dbt_project/`** — staging → gold models with `not_null`/`unique` tests and
  one unit test for dedup logic.
- Result: **PASS=11, WARN=0, ERROR=0**.

---

## 4. Verification results

### 4.1 Smoke test (`make verify`)

```
RESULT: 16/16 checks — ALL PASS
```

Checks cover: extract, dedup, quarantine, Gold, streaming idempotency, embedding
ingestion, trace flattening, eval curation, decontamination, ASOF anti-leak, and
knowledge-graph queries.

### 4.2 Unit tests (`make test`)

```
18 passed in 0.35s
```

### 4.3 Flywheel run (`make flywheel`)

```
spans landed in Bronze   : 21 (from 8 traces)
eval golden rows         : 2
preference pairs (raw)   : 3
preference pairs (clean) : 1  (2 dropped by decontamination)
rows where naive join LEAKED a future value: 2
```

Full output is archived in `submission/VERIFY_OUTPUT.txt`.

---

## 5. Bonus challenge

### 5.1 Problem statement

**Design doc:** `bonus/DESIGN.md` (839 words)

Topic: a **Vietnamese e-commerce customer-support chatbot flywheel** — turning
production agent traces into eval and DPO datasets while handling paraphrased
Vietnamese/English prompts, PDPL (Law 91/2025) constraints, and limited infra
budget.

Key decisions documented:

- Immutable Bronze vs edit-on-ingest
- Nightly batch vs hourly micro-batch
- Span-level PII quarantine vs blocking whole traces
- Character 13-gram fuzzy decontamination vs embedding similarity
- ASOF feature joins for train/serve parity
- On-prem CPU processing vs cross-border GPU embedding APIs

**Rejected alternative:** exact-match-only decontamination — paraphrased eval
prompts silently leak into training data and inflate offline metrics.

### 5.2 Prototype

| File | Purpose |
|---|---|
| `pipeline/fuzzy_decontam.py` | Character 13-gram Jaccard decontamination (NFC-normalized) |
| `bonus/fuzzy_demo.py` | Runnable demo — EN and VI paraphrases caught by fuzzy match |

Run: `make bonus` or `python bonus/fuzzy_demo.py`

**Demo finding:** exact match kept paraphrased prompts that fuzzy 13-gram overlap
correctly removed in both English and Vietnamese examples.

---

## 6. Reflection summary

See `submission/REFLECTION.md` for full answers. Key takeaways:

1. **Decontamination** is the most silent failure point in the flywheel — no
   pipeline error, but eval metrics lie if prompts leak into DPO pairs.
2. Skipping decontamination causes memorization of eval answers; fresh prompts
   or live A/B testing expose the gap.
3. **Point-in-time joins** are mandatory for features like credit limits at loan
   application — joining current balance leaks future behavior.
4. **Knowledge graphs** excel at multi-hop questions; **vector RAG** suffices for
   direct policy lookups.

---

## 7. How to reproduce

```bash
# Setup (once)
make setup
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Core pipeline
make verify    # 16/16 ALL PASS
make run       # Medallion ETL
make flywheel  # Agent traces → datasets
make test      # 18 pytest tests

# Optional
make kg        # Knowledge graph demo
make bonus     # Fuzzy decontamination demo
make dbt       # dbt build (Python 3.10–3.13)
```

---

## 8. Submission artifacts

| Artifact | Location |
|---|---|
| Smoke test output | `submission/VERIFY_OUTPUT.txt` |
| Reflection (≤ 200 words) | `submission/REFLECTION.md` |
| Eval golden set | `datasets/eval_golden.jsonl` |
| DPO preference pairs | `datasets/preference_pairs.jsonl` |
| Bonus design | `bonus/DESIGN.md` |
| Bonus prototype | `bonus/fuzzy_demo.py`, `pipeline/fuzzy_decontam.py` |
| This report | `report.md` |

---

## 9. Conclusion

The Day 17 pipeline successfully demonstrates production-shaped data engineering
for AI systems: gated Medallion ETL, an agent-data flywheel with decontamination,
point-in-time feature correctness, and knowledge-graph vs vector retrieval
tradeoffs. The bonus extends decontamination toward fuzzy matching for
Vietnamese paraphrases — a realistic gap in exact-match pipelines. All automated
checks pass and the project is ready for LMS submission via a public GitHub URL.

---

*Submitted by Võ Thanh Hiệp (2A202600836)*
