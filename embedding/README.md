# Embeddings Hands-On: Dense vs Sparse vs Hybrid (RRF) on Elasticsearch

This project is built around the ELK-as-vector-DB setup you already run at ShadowPulse,
so the concepts transfer directly instead of being a generic toy demo.

## What's in here

- `docker-compose.yml` — ES 8.15 + Kibana, security disabled for local dev
- `corpus.py` — 20 synthetic threat-intel/social-media style posts, deliberately
  designed with paraphrase pairs and an exact-term-only pair (see comments in the file)
- `embedder.py` — swappable embedding backend: local (`sentence-transformers`, free)
  or Voyage AI (Anthropic's recommended embedding partner — **Anthropic doesn't build
  its own embedding model**, Claude does text generation, embeddings are a different
  training objective, so they point to Voyage instead)
- `setup_and_ingest.py` — creates the index (`text` + `dense_vector`, dimension
  auto-detected from the embedder), embeds the corpus, bulk-indexes
- `search_demo.py` — runs BM25, dense kNN, RRF hybrid, and cross-encoder reranking
  side by side on the same query
- `rerank.py` — cross-encoder reranking stage (bi-encoder retrieval + cross-encoder
  rerank on a small candidate set — the same two-stage pattern your production
  system uses)
- `eval.py` — a tiny hand-labeled eval set + Hit Rate@K scoring across all four
  methods, a first taste of formal eval methodology on a corpus small enough to
  reason about by hand

## Switching embedding backend

Edit `embedder.py`:

```python
BACKEND = "local"   # free, no API key, runs on your machine
# or
BACKEND = "voyage"  # needs VOYAGE_API_KEY env var, Anthropic-recommended, paid API
```

For Voyage:
```bash
export VOYAGE_API_KEY="your-key-here"
```
Get a key at https://dashboard.voyageai.com — they have a free tier for experimentation.

Note: dimension is auto-detected, so switching backends and re-running
`setup_and_ingest.py` just works — it rebuilds the index at whatever dimension
the new backend produces (MiniLM: 384, Voyage voyage-3-large: 1024).

## Setup

```bash
# 1. Start Elasticsearch + Kibana
docker compose up -d

# wait ~20-30s for ES to be healthy, then check:
curl http://localhost:9200/_cluster/health

# 2. Python env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Build the index + embed + ingest
python setup_and_ingest.py

# 4. Run queries
python search_demo.py "bots coordinating to push the same message"
```

Note: `sentence-transformers` will download the MiniLM model (~80MB) from Hugging Face
on first run — needs internet access once, then it's cached locally.

## Exercises — do these in order, and actually think about *why* before reading the "what to notice"

### 1. Semantic paraphrase (dense should win)
```bash
python search_demo.py "bots coordinating to push the same message"
```
`doc_01`, `doc_02`, `doc_03` describe the same coordinated-posting event using almost
completely different words. **What to notice:** BM25 likely ranks these lower or misses
some (little word overlap with the query). Dense kNN should surface all three near the
top because the *meaning* matches even though the wording doesn't. This is the core
value proposition of embeddings.

### 2. Exact technical term (BM25 should win, or at least tie)
```bash
python search_demo.py "CVE-2024-38112"
```
Only `doc_10` and `doc_20` contain this exact string. **What to notice:** BM25 nails this
immediately — exact string match is its whole job. Check whether dense search also finds
it, and at what rank/score — this is where you should form your own opinion on whether
dense alone would have been "good enough" here, or whether you'd have missed/underranked
it without the sparse signal. This is the real justification for hybrid retrieval that
you should be able to articulate in an interview, using your own numbers, not mine.

### 3. Coded/evasive language (the one closest to your actual production problem)
```bash
python search_demo.py "people using symbols instead of slurs to target a group"
```
`doc_15` and `doc_16` describe evasive, coded language used to bypass keyword filters,
using phrasing designed to have low lexical overlap with an "obvious" query. **What to
notice:** this is the closest analog in this toy corpus to your real hateful-content
detection problem — content designed specifically to evade lexical/keyword filtering.
Compare how BM25 handles this versus dense.

### 4. Break it on purpose
Try a query that's semantically adjacent but genuinely ambiguous (e.g. `"malware demanding
payment"` — should hit both `doc_06`/`doc_07` (ransomware) and maybe pull in unrelated fraud
docs). Look at the RRF hybrid scores and think about whether the RRF_K constant (currently 60,
the standard default) is doing what you'd want, or whether you'd tune it for your use case.

## Reranking and eval (now built in)

```bash
# See BM25 / dense / RRF / cross-encoder-reranked side by side on one query:
python search_demo.py "bots coordinating to push the same message"

# Score all four methods against a hand-labeled eval set (Hit Rate @ K):
python eval.py
```

Things to actually look at, not just run:
- **In `search_demo.py` output**, compare the RRF ranking to the reranked ranking on
  the same query. Where do they disagree? The cross-encoder saw the query and each
  document *together*; RRF only ever compared independently-computed vectors. Form an
  opinion on whether the reorder is actually better before reading anything else — that
  judgment call is what you're being hired to make.
- **In `eval.py` output**, look at which specific queries each method fails on, not
  just the aggregate hit-rate. A 100% hit-rate on 6 queries proves nothing statistically
  — the value here is the *habit* of writing expectations down before looking at
  results, and the vocabulary (Hit Rate@K) for talking about retrieval quality precisely
  instead of "it seems to work."

## Where to go next (once this feels solid)

1. **Swap the embedding backend and re-run everything** — flip `embedder.py` to
   `BACKEND = "voyage"` (or try `BAAI/bge-small-en-v1.5` locally) and re-run
   `setup_and_ingest.py` then `eval.py`. Compare the Hit Rate@K numbers directly —
   this turns "embedding model quality" from an abstract idea into a number you
   produced yourself.
2. **Look at it in Kibana** — open `http://localhost:5601`, create a data view on
   `embed_demo`, and browse the indexed docs. Not analytically necessary for this
   exercise, but worth doing once since you'll want Kibana fluency regardless.
3. **Grow the eval set** — add 10-15 more (query, expected doc_id) pairs, including
   some deliberately adversarial ones (queries with expected-empty results, or
   multi-topic queries with more than one right answer) to stress-test the metric
   itself, not just the retrieval.
4. **Try it against your real ShadowPulse-style data** — once this feels solid on the
   toy corpus, the real test is whether the same four-method comparison and eval habit
   transfers cleanly to your actual production content patterns.
