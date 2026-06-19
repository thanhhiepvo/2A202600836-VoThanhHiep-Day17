# Reflection — Day 17 (≤ 200 words)

1. **The flywheel.** **Decontamination** breaks most silently: eval prompts can leak into DPO pairs without any pipeline error. I'd detect it by diffing normalized prompts across eval vs training sets and alerting on overlap; a never-touched eval slice should stay flat while the leaky set inflates.

2. **Decontamination.** Skipping it trains on the exact questions you grade on, so the model memorizes eval answers. Benchmarks rise artificially; a fresh prompt set or live A/B exposes the gap.

3. **Point-in-time.** A user's **credit limit at loan application** must use debt known *at or before* approval. Joining today's balance leaks future purchases and overstates creditworthiness.

4. **Graph vs vector.** The **knowledge graph** handles multi-hop questions like "where does a widget ship from?" (widget → accessory → Hanoi). **Vector RAG** is enough for direct lookups like "what is the widget return window?" — a graph is overkill there.
