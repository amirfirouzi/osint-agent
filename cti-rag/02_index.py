"""2. Read every .jsonl in data/corpus/, chunk it, embed it, load into pgvector.

This is the whole ingest half of the RAG pipeline in one file. Re-running it
drops and rebuilds the table — that's what you want while you're experimenting.

    python 02_index.py

Takes ~2-4 min on a MacBook the first time (model download + embedding).
"""
import json
import os

import config

CREATE_SQL = f"""
CREATE EXTENSION IF NOT EXISTS vector;

DROP TABLE IF EXISTS chunks;
CREATE TABLE chunks (
    id        bigserial PRIMARY KEY,
    chunk_id  text UNIQUE,
    doc_id    text,
    source    text,
    title     text,
    text      text,
    url       text,
    metadata  jsonb,
    embedding vector({config.EMBED_DIM})
);
"""

# Built AFTER the rows are inserted — index-then-insert is much slower.
# vector_cosine_ops matches our normalised embeddings and the <=> operator.
INDEX_SQL = """
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON chunks (doc_id);
CREATE INDEX ON chunks (source);
"""


def load_documents():
    """Every .jsonl in data/corpus/ — attack, cisa, kev, reports."""
    docs = []
    for fname in sorted(os.listdir(config.CORPUS_DIR)):
        if not fname.endswith(".jsonl"):
            continue
        path = os.path.join(config.CORPUS_DIR, fname)
        with open(path, encoding="utf-8") as fh:
            n = 0
            for line in fh:
                if line.strip():
                    docs.append(json.loads(line))
                    n += 1
        print(f"  {fname}: {n} documents")
    return docs


def chunk(doc):
    """Fixed-size chunks with overlap. The naive baseline from the AWS slide.

    Words, not tokens — close enough, one less dependency. The title is glued to
    the front of every chunk so a chunk from page 40 still knows what document
    it came from. Cheap, and it helps more than you'd expect.
    """
    words = doc["text"].split()
    if not words:
        return []
    step = config.CHUNK_WORDS - config.OVERLAP_WORDS
    out = []
    for i in range(0, len(words), step):
        piece = " ".join(words[i:i + config.CHUNK_WORDS])
        if not piece.strip():
            continue
        out.append({
            "chunk_id": f"{doc['doc_id']}#{len(out)}",
            "doc_id": doc["doc_id"],
            "source": doc.get("source", "unknown"),
            "title": doc.get("title", ""),
            "text": f"{doc.get('title', '')}\n\n{piece}",
            "url": doc.get("url"),
            "metadata": doc.get("metadata", {}),
        })
        if i + config.CHUNK_WORDS >= len(words):
            break
    return out


def main():
    print("reading corpus...")
    docs = load_documents()
    if not docs:
        print(f"nothing in {config.CORPUS_DIR}/ — put your .jsonl files there")
        return

    chunks = []
    for d in docs:
        chunks.extend(chunk(d))
    print(f"\n{len(docs):,} documents -> {len(chunks):,} chunks")

    print("\nembedding (first run downloads the model)...")
    vectors = config.embed_docs([c["text"] for c in chunks])

    print("\nloading into postgres...")
    with config.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_SQL)
            # copy is much faster than executemany for this many rows
            with cur.copy(
                "COPY chunks (chunk_id, doc_id, source, title, text, url, metadata, embedding) "
                "FROM STDIN"
            ) as copy:
                for c, v in zip(chunks, vectors):
                    copy.write_row((
                        c["chunk_id"], c["doc_id"], c["source"], c["title"],
                        c["text"], c["url"], json.dumps(c["metadata"]),
                        "[" + ",".join(f"{x:.6f}" for x in v) + "]",
                    ))
            print("  building hnsw index...")
            cur.execute(INDEX_SQL)
        conn.commit()

    print(f"\ndone — {len(chunks):,} chunks in pgvector")


if __name__ == "__main__":
    main()
