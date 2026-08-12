# rag — a hands-on RAG project

Ask a threat-intel question, see the retrieval steps, the evidence, and a cited
answer. Built in phases so each piece of the pipeline is something you tuned,
not something you copied.

```
config.py             settings shared by every script
01_pdfs_to_jsonl.py   PDFs  -> data/corpus/reports.jsonl
02_index.py           corpus -> chunks -> embeddings -> pgvector
03_rag.py             search -> prompt -> cited answer   (also a library)
04_eval.py            score retrieval against questions.yaml
app.py + web/         the web UI
questions.yaml        your answer key
```

## Setup (once)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d          # pgvector on localhost:5433
export ANTHROPIC_API_KEY=sk-ant-...
```

Put your `attack.jsonl`, `cisa.jsonl`, `kev.jsonl` in `data/corpus/`
and your PDFs in `data/pdfs/`.

## Run

```bash
python 01_pdfs_to_jsonl.py            # PDFs -> jsonl
python 02_index.py                    # chunk + embed + load  (~2-4 min first run)
python 03_rag.py "What is T1486?"     # sanity check
uvicorn app:app --reload              # http://127.0.0.1:8000
python 04_eval.py                     # the number that justifies every later phase
```

Re-running `02_index.py` drops and rebuilds the table. That's intentional —
you'll do it a lot.

## Phases

Each phase changes ONE file, then you re-run `04_eval.py` and compare.

| # | What | File you edit | Done when |
|---|------|---------------|-----------|
| 1 | Naive RAG end to end | — | UI answers, `04_eval.py` prints a baseline |
| 2 | Better PDF parsing | `01_pdfs_to_jsonl.py` | the IOC-table question improves |
| 3 | Chunking strategies | `02_index.py` (`chunk()`) | one strategy wins on numbers |
| 4 | Hybrid search + reranking + query rewriting | `03_rag.py` (`search()`) | exact_id and multi_hop recover |
| 5 | Citations, refusal, structured output | `03_rag.py` (`SYSTEM`) | unanswerable questions get refused |
| 6 | Same thing on Bedrock Knowledge Bases | new script | you can state what managed RAG cost you |

**Rule: never start a phase without a score from the last one.**

## What Phase 1 should show you

Run these in the UI and watch it fail in specific ways — each failure is the
argument for a later phase:

- `What is T1059.003?` — embeddings don't treat identifiers as identifiers.
  Expect the wrong technique. → Phase 4, hybrid search.
- `Midnight Blizzard ... initial access?` — the alias appears only in the group
  document; the behaviour only in procedure documents that say "APT29". No
  lexical or semantic bridge. → Phase 4, query rewriting.
- `What is the CVSS score of CVE-2024-3400?` — not in the corpus. See whether it
  refuses or invents one. → Phase 5.
- Set top-k to 1, then 20. Watch precision and answer quality pull apart.
- Delete `QUERY_PREFIX` in `config.py`, re-run `04_eval.py`, put it back. That's
  what a silent RAG bug costs.
