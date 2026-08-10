"""
Runs the SAME query FOUR ways against the index built by setup_and_ingest.py:
  1. BM25 (sparse/lexical)      -- exact/keyword matching
  2. Dense kNN (embeddings)     -- semantic/meaning matching
  3. Reciprocal Rank Fusion     -- hybrid of the two
  4. Cross-encoder rerank       -- precise reorder of the top RRF candidates

Stage 4 mirrors your production pattern: fast approximate retrieval (1-3),
then a slower precise reranker on a small candidate set (4).

Run: python search_demo.py "your query here"
"""

import sys
from elasticsearch import Elasticsearch
from embedder import Embedder
from rerank import rerank

INDEX_NAME = "embed_demo"
ES_URL = "http://localhost:9200"
TOP_K = 5
RERANK_CANDIDATES = 10  # how many RRF results to feed the reranker
RRF_K = 60  # standard RRF smoothing constant


def bm25_search(es: Elasticsearch, query: str, k: int = TOP_K):
    resp = es.search(
        index=INDEX_NAME,
        query={"match": {"text": query}},
        size=k,
    )
    return [(hit["_id"], hit["_score"], hit["_source"]["text"]) for hit in resp["hits"]["hits"]]


def dense_search(es: Elasticsearch, embedder: Embedder, query: str, k: int = TOP_K):
    qvec = embedder.embed(query, input_type="query")
    resp = es.search(
        index=INDEX_NAME,
        knn={
            "field": "embedding",
            "query_vector": qvec,
            "k": k,
            "num_candidates": 50,
        },
        size=k,
    )
    return [(hit["_id"], hit["_score"], hit["_source"]["text"]) for hit in resp["hits"]["hits"]]


def reciprocal_rank_fusion(bm25_results, dense_results, k: int = RRF_K):
    scores = {}
    texts = {}

    for rank, (doc_id, _score, text) in enumerate(bm25_results, start=1):
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)
        texts[doc_id] = text

    for rank, (doc_id, _score, text) in enumerate(dense_results, start=1):
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)
        texts[doc_id] = text

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [(doc_id, score, texts[doc_id]) for doc_id, score in fused]


def print_results(title, results):
    print(f"\n--- {title} ---")
    if not results:
        print("  (no results)")
    for doc_id, score, text in results:
        print(f"  [{doc_id}]  score={score:.4f}  {text[:90]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python search_demo.py "your query here"')
        print("\nTry these to see dense vs sparse vs reranked behave differently:")
        print('  python search_demo.py "bots coordinating to push the same message"')
        print('  python search_demo.py "CVE-2024-38112"')
        print('  python search_demo.py "people using symbols instead of slurs to target a group"')
        sys.exit(1)

    query = sys.argv[1]
    print(f'Query: "{query}"')

    es = Elasticsearch(ES_URL)
    embedder = Embedder()

    bm25_results = bm25_search(es, query)
    dense_results = dense_search(es, embedder, query)
    fused_results = reciprocal_rank_fusion(bm25_results, dense_results)

    reranked_results = rerank(query, fused_results[:RERANK_CANDIDATES])

    print_results("BM25 (lexical)", bm25_results)
    print_results("Dense kNN (semantic)", dense_results)
    print_results("RRF Hybrid", fused_results[:TOP_K])
    print_results(f"Cross-Encoder Reranked (top {RERANK_CANDIDATES} RRF candidates, reordered)", reranked_results[:TOP_K])
