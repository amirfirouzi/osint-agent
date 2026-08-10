"""
Embedding backend abstraction. Two options:

  LOCAL  - sentence-transformers, runs on your machine, free, no API key.
           Good for offline iteration and understanding mechanics.

  VOYAGE - Voyage AI, Anthropic's recommended embedding provider (Anthropic
           doesn't build its own embedding model -- Claude does text
           generation, embeddings are a different training objective
           (contrastive learning vs next-token prediction), so Anthropic
           partners with Voyage instead of competing in that space).
           Needs VOYAGE_API_KEY env var. Paid API, but strong quality
           (voyage-3-large is near the top of MTEB as of early 2026).

Switch backends by changing BACKEND below. Dimension is auto-detected from
a live embedding call, so setup_and_ingest.py doesn't need to hardcode it.
"""

import os
import voyageai
from dotenv import load_dotenv

BACKEND = "voyage"  # "local" or "voyage"

LOCAL_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# Try swapping to "BAAI/bge-small-en-v1.5" to compare quality on the same corpus.

VOYAGE_MODEL_NAME = "voyage-3-large"

load_dotenv()

class Embedder:
    def __init__(self, backend: str = BACKEND):
        self.backend = backend
        self._dim = None

        if backend == "local":
            from sentence_transformers import SentenceTransformer
            self.model_name = LOCAL_MODEL_NAME
            self._model = SentenceTransformer(self.model_name)

        elif backend == "voyage":

            api_key = os.getenv("VOYAGE_API_KEY")
            assert api_key, "Set VOYAGE_API_KEY env var to use the voyage backend."
            self.model_name = VOYAGE_MODEL_NAME
            self._client = voyageai.Client(api_key=api_key)

        else:
            raise ValueError(f"Unknown backend: {backend}")

    def embed(self, texts, input_type: str = "document"):
        """
        input_type matters for Voyage: 'document' when indexing, 'query' when
        searching. Voyage embeds queries and documents slightly asymmetrically
        for better retrieval quality -- worth knowing this pattern exists,
        some providers do this and some don't.
        """
        if isinstance(texts, str):
            texts = [texts]
            single = True
        else:
            single = False

        if self.backend == "local":
            vecs = self._model.encode(texts, normalize_embeddings=True).tolist()

        elif self.backend == "voyage":
            resp = self._client.embed(texts, model=self.model_name, input_type=input_type)
            vecs = resp.embeddings

        if self._dim is None:
            self._dim = len(vecs[0])

        return vecs[0] if single else vecs

    @property
    def dim(self):
        if self._dim is None:
            # trigger a dummy call to learn the dimension
            self.embed("dimension probe")
        return self._dim
