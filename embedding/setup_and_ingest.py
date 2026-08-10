"""
Step 1: embed the corpus (local model or Voyage AI, see embedder.py)
Step 2: create the index with a dense_vector field sized to match
Step 3: bulk-index into Elasticsearch

Run: python setup_and_ingest.py
"""

from elasticsearch import Elasticsearch, helpers
from corpus import DOCS
from embedder import Embedder

INDEX_NAME = "embed_demo"
ES_URL = "http://localhost:9200"


def build_index(es: Elasticsearch, dim: int):
    if es.indices.exists(index=INDEX_NAME):
        print(f"Deleting existing index '{INDEX_NAME}'...")
        es.indices.delete(index=INDEX_NAME)

    mapping = {
        "mappings": {
            "properties": {
                "text": {"type": "text"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": dim,
                    "index": True,
                    "similarity": "cosine",
                },
            }
        }
    }
    es.indices.create(index=INDEX_NAME, body=mapping)
    print(f"Created index '{INDEX_NAME}' with a {dim}-dim cosine dense_vector field.")


def embed_and_index(es: Elasticsearch, embedder: Embedder):
    texts = [d["text"] for d in DOCS]
    print(f"Embedding {len(texts)} documents with backend='{embedder.backend}' model='{embedder.model_name}'...")
    vectors = embedder.embed(texts, input_type="document")

    actions = [
        {
            "_index": INDEX_NAME,
            "_id": doc["id"],
            "_source": {"text": doc["text"], "embedding": vec},
        }
        for doc, vec in zip(DOCS, vectors)
    ]
    helpers.bulk(es, actions)
    es.indices.refresh(index=INDEX_NAME)
    print(f"Indexed {len(actions)} documents.")


if __name__ == "__main__":
    es = Elasticsearch(ES_URL)
    assert es.ping(), f"Could not reach Elasticsearch at {ES_URL} -- is Docker running?"

    embedder = Embedder()  # backend set in embedder.py

    build_index(es, embedder.dim)
    embed_and_index(es, embedder)

    print("\nDone. Now run: python search_demo.py \"your query here\"")
