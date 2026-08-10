"""
Cross-encoder reranking.

Why this exists as a SEPARATE stage from retrieval:
- Bi-encoder embeddings (what setup_and_ingest.py builds) encode the query and
  each document INDEPENDENTLY, then compare vectors. Fast (one query encode +
  a vector search), but the model never actually looks at the query and a
  document TOGETHER -- it's comparing two separate summaries.
- A cross-encoder takes (query, document) as a SINGLE joint input and outputs
  one relevance score. This lets it model actual query-document interaction
  (e.g. "does this document actually answer THIS query"), which is more
  accurate -- but it's O(n) expensive model calls, so you only run it on a
  small candidate set (typically top 10-50 from retrieval), never the full
  corpus. That's exactly the two-stage pattern your production reranker uses.
"""

from sentence_transformers import CrossEncoder

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_model = None


def get_reranker():
    global _model
    if _model is None:
        _model = CrossEncoder(RERANKER_MODEL)
    return _model


def rerank(query: str, candidates: list):
    """
    candidates: list of (doc_id, score, text) tuples, e.g. from RRF fusion.
    Returns the same tuples reordered by cross-encoder relevance score,
    with the RRF score replaced by the cross-encoder score so you can see
    both rankings side by side.
    """
    if not candidates:
        return []

    model = get_reranker()
    pairs = [[query, text] for _doc_id, _score, text in candidates]
    ce_scores = model.predict(pairs)

    reranked = [
        (doc_id, float(ce_score), text)
        for (doc_id, _rrf_score, text), ce_score in zip(candidates, ce_scores)
    ]
    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked
