# Embeddings Hands-On: Dense vs Sparse vs Hybrid (RRF) on Elasticsearch

This project is built around the ELK-as-vector-DB setup you already run at ShadowPulse,
so the concepts transfer directly instead of being a generic toy demo.

## What's in here

- `docker-compose.yml` — ES 8.15 + Kibana, security disabled for local dev
- `corpus.py` — 20 synthetic threat-intel/social-media style posts, deliberately
  designed with paraphrase pairs and an exact-term-only pair (see comments in the file)
- `setup_and_ingest.py` — creates the index (`text` + `dense_vector` fields), embeds
  the corpus locally with `sentence-transformers/all-MiniLM-L6-v2`, bulk-indexes
- `search_demo.py` — runs BM25, dense kNN, and RRF hybrid search side by side on
  the same query

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

## Where to go next (once this feels solid)

1. **Swap the embedding model** — try `BAAI/bge-small-en-v1.5` instead of MiniLM (just
   change `MODEL_NAME` in both scripts, dimension is different so re-run setup) and see
   if the paraphrase/coded-language cases rank differently. This gives you a real, felt
   sense of "embedding model quality" instead of an abstract idea.
2. **Add a reranker** — this is the natural next step given your production system
   already has one. Take the top ~10 RRF results and rerank them with a cross-encoder
   (`sentence-transformers` also ships `cross-encoder/ms-marco-MiniLM-L-6-v2`) and compare
   the reordering against plain RRF. This is the exact mechanism worth being able to
   explain in an interview: bi-encoder retrieval (fast, approximate) + cross-encoder
   rerank (slow, precise, only on a small candidate set).
3. **Look at it in Kibana** — open `http://localhost:5601`, create a data view on
   `embed_demo`, and browse the indexed docs. Not analytically necessary for this
   exercise, but worth doing once since you'll want Kibana fluency regardless.
4. **Build a tiny eval set** — write down 5-10 (query, expected doc_id) pairs from this
   corpus yourself, then score BM25 vs dense vs RRF with simple hit-rate@k. This is a
   first, small taste of the "formal eval methodology" gap flagged in your roadmap —
   doing it on a toy corpus first, before your real production data, is the right order.
