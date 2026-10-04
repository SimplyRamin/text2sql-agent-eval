---
title: Text2SQL Agent Eval
emoji: 🧮
colorFrom: indigo
colorTo: gray
sdk: gradio
sdk_version: "6.29.1"
python_version: "3.11"
app_file: demo/app.py
pinned: false
license: mit
short_description: Replay of a text-to-SQL eval — baseline vs routed agent
---

# text2sql-agent-eval — results explorer

A replay demo of a text-to-SQL agent evaluation: 100 stratified questions
over an Olist e-commerce warehouse, 5 difficulty tiers, 4 architectures
(local/hosted × dumb baseline/routed agent). Nothing runs live here —
this explores the committed reference results.

Full project, source code, and build log: [github.com/SimplyRamin/text2sql-agent-eval](https://github.com/SimplyRamin/text2sql-agent-eval)

**A note on the numbers:** these are single runs. Retry temperature
(0.4) and hosted API calls both carry inherent run-to-run variance —
read results as accuracy ± a few points, not exact figures. See
`FAILURE_TAXONOMY.md` in the repo for the full failure-mode breakdown.