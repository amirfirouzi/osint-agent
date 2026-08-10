# cti-rag — a CTI analyst copilot, built one failure mode at a time

Ask: *"Midnight Blizzard is reported in our environment — what initial access
methods should we hunt for?"* Get: a grounded answer, the evidence it rests on,
and every step the pipeline took to find it.

The corpus is chosen to break naive RAG in four specific ways: exact
identifiers (`CVE-2024-3400`, `T1566.002`), actor aliases (APT29 = Cozy Bear =
Midnight Blizzard), superseded advisories, and PDF tables. Each phase fixes one.

---

## Phase map

| Phase | Goal | Gate |
|---|---|---|
| **0** | Corpus + eval set + BM25 floor | `ctirag evals validate` passes, baseline scored |
| 1 | Naive dense RAG + **web UI** (steps / evidence / answer) | beats or matches BM25 floor |
| 2 | Layout-aware parsing (Textract / unstructured) | IOC-table question recovers |
| 3 | Chunking: fixed / semantic / parent-child / sentence-window | one strategy wins on numbers |
| 4 | Hybrid + RRF + metadata filters + reranker + query rewrite | recall@10 up, alias questions fixed |
| 5 | Citations, refusal, structured output | unanswerable set refused, not answered |
| 6 | Bedrock Knowledge Bases + OpenSearch Serverless | same eval set, compare quality/latency/cost |
| 7 | Incremental ingest, re-embedding cost, caching, logging | rebuild is cheap and observable |

**Rule: never move to the next phase without a score from the current one.**

---

## Phase 0 — runbook

### 1. Prerequisites

```bash
python3 --version          # need 3.11+
git init                   # commit after every phase; you will want the diff
```

No Docker, no database, no AWS account yet. Phase 0 is deliberately dependency-light
so nothing can fail for reasons unrelated to what you're learning.

### 2. Install

```bash
cd cti-rag
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
ctirag --help
```

### 3. Fetch the corpus

```bash
ctirag fetch attack     # ~50 MB download, ~5,500 documents
ctirag fetch kev        # CISA Known Exploited Vulnerabilities
ctirag fetch cisa       # 60 advisories, polite crawl, ~2 minutes
```

Then drop **8–15 vendor APT report PDFs** into `data/raw/reports/` by hand
(`ctirag fetch reports` prints suggestions). Get at least three with tables of
IOCs — those are the ones that break in Phase 1 and get fixed in Phase 2.

```bash
ctirag fetch reports
ctirag inventory
```

`inventory` is worth reading, not skipping. Note the median document length
against the p95 — that spread is what makes a single fixed chunk size wrong, and
it's the argument you'll test in Phase 3.

### 4. Build the eval set

```bash
ctirag evals generate     # ~28 questions with ground truth derived from ATT&CK
ctirag evals label        # hand-label the rest, interactively (~20 min)
```

The generated questions are free but uniform. The hand-written ones in
`evals/questions.handwritten.yaml` are where the real difficulty lives — read
them, and rewrite `hw017`, `hw024`, `hw025` to point at documents that actually
exist in *your* snapshot.

### 5. The gate

```bash
ctirag evals validate     # must print PASS
python -m pytest -q       # must be green
```

### 6. The floor

```bash
ctirag evals baseline
```

This is your control group: BM25 over whole documents, no embeddings, no LLM.
Write the numbers down. A dense pipeline that doesn't beat this is not working,
however impressive the demo looks.

**Phase 0 is done when:** `validate` prints PASS, tests are green, and
`evals/results.bm25-baseline.json` exists.

### 7. Read your own failures before moving on

```bash
ctirag search "What does T1059.003 describe?" -k 5
```

You'll see short procedure documents outranking the authoritative technique
document, because BM25 length-normalisation punishes long documents that mention
an ID many times less densely. That's not a bug to fix now — it's the first
thing your Phase 4 reranker has to beat.

---

## Layout

```
src/ctirag/
  config.py            paths, source URLs, limits
  corpus.py            Document model, JSONL store, manifest
  trace.py             PipelineTrace — the contract the UI renders
  cli.py               ctirag entry point
  sources/
    attack.py          ATT&CK -> technique / group / procedure docs
    advisories.py      CISA KEV + advisory HTML
    reports.py         vendor PDFs (naive extraction, on purpose)
  retrieval/
    bm25.py            the floor
  evals/
    schema.py          Question model
    generate.py        derived questions with exact ground truth
    label.py           interactive labeling
    metrics.py         recall@k, hit@k, MRR
    validate.py        the Phase 0 gate
evals/                 question sets + results
data/                  corpus + raw downloads (gitignored)
```

## Design notes worth knowing before Phase 1

**Why procedures are separate documents.** ATT&CK group descriptions list
aliases; technique descriptions are generic and never name an actor; only the
procedure text (*"APT29 has used…"*) links them. Answering an alias question
therefore needs two hops through documents that don't reference each other. This
is the failure mode that makes people conclude "RAG doesn't work" — you'll fix
it in Phase 4 with query rewriting, not with a bigger model.

**Why technique IDs live in group metadata, not group text.** If the group
document listed its technique IDs, every multi-hop question would collapse into
a one-hop lookup and your eval set would flatter the system.

**Why the trace object exists in Phase 0.** Every stage appends a `Step` rather
than hiding work inside a function, so the Phase 1 UI renders new pipeline
stages for free, and you debug retrieval by looking at it rather than by adding
print statements.
