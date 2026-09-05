# Autoresearch Session — Singapore Geospatial Showcase Project Scouting

- Started: 2026-09-04
- Mode: **DISCOVERY (adapted)**. No benchmark command / numeric metric exists for this task.
  The loop optimizes for an evidence-backed ranking of candidate project use cases.
  Each iteration = gather evidence → evaluate candidates → keep / drop / promote decision.

## Objective

Identify a portfolio-grade geospatial project idea for Singapore, inspired by
`github.com/Vorld/singapore-travel-time-map`, grounded in six evidence channels:

1. **Baseline** — the example repo itself + inventory of existing Singapore geospatial repos (gh CLI)
2. **International map demos** — GitHub search via `gh` CLI
3. **Web search** — degoog meta-search MCP
4. **Interactive browsing** — chromiumfish MCP (JS-rendered pages scrapers can't read)
5. **URL reading** — pi-scraper (`web_scrape` / `web_extract`)
6. **Research literature** — alpha tools (`alpha_search`, `alpha_get_paper`) for use cases we can apply

## Loop config

| Field | Value |
|---|---|
| Optimization target | candidate-use-case quality score (qualitative) |
| Metric / direction | decision = keep / drop / promote, logged per iteration |
| Benchmark command | n/a (discovery loop) |
| Files in scope | session + artifact files in this directory only |
| Environment | local (gh CLI 2.98.0, authed as siva-sub) |
| Max iterations | 8 |
| Optional tools | `init_experiment` / `run_experiment` / `log_experiment` NOT VISIBLE → file-based logging in `autoresearch.jsonl` |

## Deliverable

One canonical artifact: `outputs/singapore-geospatial-usecase-scouting.md`
(ranked candidate use cases, evidence links, data sources, recommended build plan).

## Iteration ledger

| # | Action | Decision |
|---|--------|----------|
| 0 | Baseline: example repo + SG landscape inventory | done: clone ideas dropped |
| 1 | International demos via gh CLI (22 queries) | done: whitespace found |
| 2 | Web + scholar search (degoog) | done |
| 3 | Research papers (alpha + OpenAlex + curl_cffi reads) | done |
| 4 | Pivot: economic-relevance pass + ground-truth data verification | done |
| 5 | Synthesis + ranking + final artifact | done → outputs/singapore-geospatial-usecase-scouting.md |
| 6 | Transplant scan: ideas from other jurisdictions → SG (gh + scholar) | done: rank1 upgraded (emissions ledger); new co-rank-2 'BTO from orbit' |
| 7 | Deep research on rank 1 (data feasibility, econ facts, methods, build plan) | done → outputs/singapore-strait-observatory-deepresearch.md (+ provenance sidecar) |
