"""Shared settings. Every script imports this."""
import os

DB_URL = os.environ.get("RAG_DB", "postgresql://rag:rag@localhost:5433/rag")

EMBED_MODEL = "BAAI/bge-small-en-v1.5"   # 384 dims, ~130 MB, runs on CPU
EMBED_DIM = 384

# BGE wants this prefix on the QUERY only, never on the documents.
# Forgetting it costs you recall and produces no error. Classic silent RAG bug.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

CHUNK_WORDS = 350        # ~500 tokens
OVERLAP_WORDS = 50

CLAUDE_MODEL = "claude-sonnet-5"

CORPUS_DIR = "data/corpus"
PDF_DIR = "data/raw/reports"


def connect():
    import psycopg
    return psycopg.connect(DB_URL)


_model = None


def get_model():
    """Loaded once per process, not once per call."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"loading {EMBED_MODEL} ...")
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def embed_docs(texts):
    return get_model().encode(
        texts, batch_size=64, normalize_embeddings=True,
        show_progress_bar=True, convert_to_numpy=True,
    )


def embed_query(text):
    return get_model().encode(
        [QUERY_PREFIX + text], normalize_embeddings=True, convert_to_numpy=True
    )[0]
