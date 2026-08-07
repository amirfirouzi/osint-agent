"""
Runs the SAME query three ways against the index built by setup_and_ingest.py:
  1. BM25 (sparse/lexical)      -- exact/keyword matching
  2. Dense kNN (embeddings)     -- semantic/meaning matching
  3. Reciprocal Rank Fusion     -- hybrid of the two

The point isn't "which one wins" -- it's SEEING where each one wins or loses
on the same query, which is the actual engineering judgment call you make
when choosing hybrid retrieval in production.

Run: python search_demo.py "your query here"
"""

import sys
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

INDEX_NAME = "embed_demo"
ES_URL = "http://localhost:9200"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 5
RRF_K = 60  # standard RRF smoothing constant


def bm25_search(es: Elasticsearch, query: str, k: int = TOP_K):
    resp = es.search(
        index=INDEX_NAME,
        query={"match": {"text": query}},
        size=k,
    )
    return [(hit["_id"], hit["_score"], hit["_source"]["text"]) for hit in resp["hits"]["hits"]]


def dense_search(es: Elasticsearch, model: SentenceTransformer, query: str, k: int = TOP_K):
    qvec = model.encode(query, normalize_embeddings=True).tolist()
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
    """
    RRF score for a doc = sum over each ranked list it appears in of 1 / (k + rank)
    Docs that rank well in BOTH lists rise to the top; a doc that's #1 in only
    one list doesn't automatically dominate a doc that's #2-#3 in both.
    """
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
        print("\nTry these to see dense vs sparse behave differently:")
        print('  python search_demo.py "bots coordinating to push the same message"')
        print('  python search_demo.py "CVE-2024-38112"')
        print('  python search_demo.py "people using symbols instead of slurs to target a group"')
        sys.exit(1)

    query = sys.argv[1]
    print(f'Query: "{query}"')

    es = Elasticsearch(ES_URL)
    model = SentenceTransformer(MODEL_NAME)

    bm25_results = bm25_search(es, query)
    dense_results = dense_search(es, model, query)
    fused_results = reciprocal_rank_fusion(bm25_results, dense_results)

    print_results("BM25 (lexical)", bm25_results)
    print_results("Dense kNN (semantic)", dense_results)
    print_results("RRF Hybrid", fused_results[:TOP_K])
