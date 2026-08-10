"""
A tiny, hand-labeled eval set: (query, expected relevant doc_ids).
This is a first, small taste of formal eval methodology -- the same idea
as RAGAS/golden-sets, just small enough to reason about by hand.

Metric used: Hit Rate @ K -- did AT LEAST ONE expected doc appear in the
top K results? Simple, interpretable, a reasonable first metric before
reaching for precision/recall/MRR/NDCG.

Run: python eval.py
"""

from elasticsearch import Elasticsearch
from embedder import Embedder
from rerank import rerank
from search_demo import bm25_search, dense_search, reciprocal_rank_fusion, INDEX_NAME, ES_URL

K = 5

# Each entry: query, and the doc_id(s) that should show up if retrieval is working.
# Written BEFORE looking at results -- that's the point of a golden set.
EVAL_SET = [
    {
        "query": "bots coordinating to push the same message",
        "expected": {"doc_01", "doc_02", "doc_03"},
    },
    {
        "query": "CVE-2024-38112",
        "expected": {"doc_10", "doc_20"},
    },
    {
        "query": "people using symbols instead of slurs to target a group",
        "expected": {"doc_15", "doc_16"},
    },
    {
        "query": "ransomware attack on hospital systems",
        "expected": {"doc_06", "doc_07"},
    },
    {
        "query": "scammers impersonating bank employees to get verification codes",
        "expected": {"doc_12", "doc_13"},
    },
    {
        "query": "critical remote code execution vulnerability in open source software",
        "expected": {"doc_20"},
    },
]


def hit_at_k(results, expected: set, k: int) -> bool:
    top_ids = {doc_id for doc_id, _score, _text in results[:k]}
    return len(top_ids & expected) > 0


def run_eval():
    es = Elasticsearch(ES_URL)
    embedder = Embedder()

    methods = ["bm25", "dense", "rrf", "reranked"]
    hits = {m: 0 for m in methods}

    for item in EVAL_SET:
        query, expected = item["query"], item["expected"]

        bm25_res = bm25_search(es, query, k=K)
        dense_res = dense_search(es, embedder, query, k=K)
        rrf_res = reciprocal_rank_fusion(bm25_res, dense_res)
        reranked_res = rerank(query, rrf_res[:10])

        results_by_method = {
            "bm25": bm25_res,
            "dense": dense_res,
            "rrf": rrf_res,
            "reranked": reranked_res,
        }

        print(f'\nQuery: "{query}"  (expected: {expected})')
        for m in methods:
            hit = hit_at_k(results_by_method[m], expected, K)
            hits[m] += int(hit)
            got_ids = [doc_id for doc_id, _s, _t in results_by_method[m][:K]]
            print(f"  {m:10s} hit@{K}={hit}   top_ids={got_ids}")

    print("\n=== Summary: Hit Rate @ K across eval set ===")
    n = len(EVAL_SET)
    for m in methods:
        print(f"  {m:10s} {hits[m]}/{n}  ({100 * hits[m] / n:.0f}%)")


if __name__ == "__main__":
    run_eval()
