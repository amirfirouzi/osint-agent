"""3. The RAG pipeline itself: search -> build prompt -> answer.

Both a library (imported by app.py and eval.py) and a script:

    python 03_rag.py "What is T1486?"
    python 03_rag.py "Explain T1566.002" --k 10
    python 03_rag.py "..." --no-answer          # retrieval only, costs nothing

`ask()` returns a dict with steps / evidence / answer. The web UI just renders
that dict, so any stage you add in a later phase shows up in the UI for free.
"""
import argparse
import os
import time
from dotenv import load_dotenv
import config

SYSTEM = """You are a cyber threat intelligence analyst assistant.

Answer ONLY from the numbered sources provided. They are your entire world.

Rules:
- Cite every factual claim with its source number, e.g. [S2]. A sentence with no
  citation is not allowed.
- If the sources don't contain the answer, say what is missing and stop. Do NOT
  fall back on what you know about CVEs, actors or techniques from training. A
  confident wrong answer is worse than "not in the provided sources".
- If the sources only partly answer, answer that part and name what's missing.
- Be concise. An analyst is reading this mid-incident."""
load_dotenv()

def search(question, k=6):
    """Vector search in pgvector.

    `<=>` is cosine DISTANCE (0 = identical), so we sort ascending and report
    similarity as 1 - distance to keep the UI readable.
    """
    qvec = "[" + ",".join(f"{x:.6f}" for x in config.embed_query(question)) + "]"
    with config.connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT chunk_id, doc_id, source, title, text, url,
                   1 - (embedding <=> %s::vector) AS score
            FROM chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (qvec, qvec, k),
        )
        rows = cur.fetchall()

    return [
        {"chunk_id": r[0], "doc_id": r[1], "source": r[2], "title": r[3],
         "text": r[4], "url": r[5], "score": round(float(r[6]), 4), "rank": i}
        for i, r in enumerate(rows, 1)
    ]


def generate(question, evidence):
    import anthropic

    if not os.getenv("ANTHROPIC_API_KEY"):
        return "(ANTHROPIC_API_KEY not set — retrieval ran, generation skipped)"
    if not evidence:
        return "Nothing retrieved, so there is nothing to answer from."

    sources = "\n\n---\n\n".join(
        f"[S{i}] doc_id={e['doc_id']} title={e['title']}\n{e['text']}"
        for i, e in enumerate(evidence, 1)
    )
    msg = anthropic.Anthropic().messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1000,
        system=SYSTEM,
        messages=[{"role": "user",
                   "content": f"Sources:\n\n{sources}\n\nQuestion: {question}"}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def ask(question, k=6, answer=True):
    """Run the pipeline and record each step, so the UI can show the work."""
    t0 = time.perf_counter()
    steps = []

    def mark(name, detail):
        steps.append({"name": name, "detail": detail,
                      "ms": round((time.perf_counter() - t0) * 1000, 1)})

    evidence = search(question, k=k)
    mark("vector_search", f"top {k} chunks from pgvector · "
                          f"{len(set(e['doc_id'] for e in evidence))} distinct documents")

    text = "(retrieval only)"
    if answer:
        text = generate(question, evidence)
        mark("generate", f"{config.CLAUDE_MODEL} · {len(text)} chars")

    return {
        "question": question,
        "steps": steps,
        "evidence": evidence,
        "answer": text,
        "total_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("-k", type=int, default=6)
    p.add_argument("--no-answer", action="store_true")
    a = p.parse_args()

    r = ask(a.question, k=a.k, answer=not a.no_answer)

    print("\nSTEPS")
    for s in r["steps"]:
        print(f"  {s['ms']:>8.1f} ms  {s['name']:<14} {s['detail']}")

    print("\nEVIDENCE")
    for i, e in enumerate(r["evidence"], 1):
        print(f"  [S{i}] {e['score']:.3f}  {e['chunk_id']}")
        print(f"        {' '.join(e['text'].split())[:140]}")

    print(f"\nANSWER  ({r['total_ms']} ms)\n")
    print(r["answer"])
