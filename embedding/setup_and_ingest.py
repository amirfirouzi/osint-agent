"""
Step 1: create the index (text field + dense_vector field)
Step 2: embed the corpus locally with sentence-transformers
Step 3: bulk-index into Elasticsearch

Run: python setup_and_ingest.py
"""

from elasticsearch import Elasticsearch, helpers
from sentence_transformers import SentenceTransformer
from corpus import DOCS

INDEX_NAME = "embed_demo"
ES_URL = "http://localhost:9200"

# all-MiniLM-L6-v2: small (80MB), fast on CPU, 384 dimensions.
# Good first model -- not state of the art, but you can FEEL the concepts
# without waiting on GPU inference. Swap this for bge-small/e5-small later
# to compare quality if you want a second data point.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384


def build_index(es: Elasticsearch):
    if es.indices.exists(index=INDEX_NAME):
        print(f"Deleting existing index '{INDEX_NAME}'...")
        es.indices.delete(index=INDEX_NAME)

    mapping = {
        "mappings": {
            "properties": {
                "text": {"type": "text"},  # BM25 (sparse/lexical) search runs on this
                "embedding": {
                    "type": "dense_vector",
                    "dims": EMBED_DIM,
                    "index": True,
                    "similarity": "cosine",  # matches how MiniLM was trained/normalized
                },
            }
        }
    }
    es.indices.create(index=INDEX_NAME, body=mapping)
    print(f"Created index '{INDEX_NAME}' with a {EMBED_DIM}-dim cosine dense_vector field.")


def embed_and_index(es: Elasticsearch, model: SentenceTransformer):
    texts = [d["text"] for d in DOCS]
    print(f"Embedding {len(texts)} documents with {MODEL_NAME}...")
    vectors = model.encode(texts, normalize_embeddings=True)  # normalize -> cosine == dot product

    actions = [
        {
            "_index": INDEX_NAME,
            "_id": doc["id"],
            "_source": {"text": doc["text"], "embedding": vec.tolist()},
        }
        for doc, vec in zip(DOCS, vectors)
    ]
    helpers.bulk(es, actions)
    es.indices.refresh(index=INDEX_NAME)
    print(f"Indexed {len(actions)} documents.")


if __name__ == "__main__":
    es = Elasticsearch(ES_URL)
    assert es.ping(), f"Could not reach Elasticsearch at {ES_URL} -- is Docker running?"

    model = SentenceTransformer(MODEL_NAME)

    build_index(es)
    embed_and_index(es, model)

    print("\nDone. Now run: python search_demo.py \"your query here\"")
