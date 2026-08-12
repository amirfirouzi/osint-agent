"""Diagnose retrieval. Run this whenever results look wrong.

    python 05_debug.py "What is T1486?" attack:T1486

It answers four questions in order, and the first one that fails is your bug:
  1. Is the document even in the table?
  2. Do the stored vectors look like real embeddings?
  3. What score/rank does the target get under EXACT search (no index)?
  4. Does the HNSW index return something different from exact search?
"""
import sys

import config

question = sys.argv[1] if len(sys.argv) > 1 else "What is T1486?"
target = sys.argv[2] if len(sys.argv) > 2 else "attack:T1486"

qvec = "[" + ",".join(f"{x:.6f}" for x in config.embed_query(question)) + "]"

with config.connect() as conn, conn.cursor() as cur:

    # 1. what's actually in the table
    cur.execute("SELECT source, count(*) FROM chunks GROUP BY source ORDER BY 1")
    print("\n1. ROWS BY SOURCE")
    for src, n in cur.fetchall():
        print(f"   {src:<10} {n:,}")

    cur.execute("SELECT chunk_id, left(text, 200) FROM chunks WHERE doc_id = %s", (target,))
    rows = cur.fetchall()
    print(f"\n   chunks for {target}: {len(rows)}")
    for cid, txt in rows[:2]:
        print(f"   {cid}: {' '.join(txt.split())[:150]}")
    if not rows:
        print(f"   >>> {target} IS NOT IN THE TABLE. Check your jsonl / re-run 02_index.py")
        sys.exit(1)

    # 2. are the vectors sane
    cur.execute("""
        SELECT count(*) FILTER (WHERE embedding IS NULL),
               round(avg(vector_norms.n)::numeric, 4),
               round(min(vector_norms.n)::numeric, 4),
               round(max(vector_norms.n)::numeric, 4)
        FROM chunks, LATERAL (SELECT vector_norm(embedding) AS n) vector_norms
    """)
    nulls, avg_n, min_n, max_n = cur.fetchone()
    print("\n2. VECTOR SANITY")
    print(f"   null embeddings : {nulls}")
    print(f"   norm avg/min/max: {avg_n} / {min_n} / {max_n}   (should all be ~1.0)")
    if nulls or (avg_n and abs(float(avg_n) - 1.0) > 0.05):
        print("   >>> vectors are wrong. Re-run 02_index.py")

    # 3. EXACT search - no index, guaranteed correct, just slower
    cur.execute("SET LOCAL enable_indexscan = off")
    cur.execute(
        """
        WITH ranked AS (
            SELECT chunk_id, doc_id, title,
                   1 - (embedding <=> %s::vector) AS score,
                   row_number() OVER (ORDER BY embedding <=> %s::vector) AS rank
            FROM chunks
        )
        SELECT chunk_id, title, round(score::numeric, 4), rank FROM ranked
        WHERE rank <= 5 OR doc_id = %s
        ORDER BY rank LIMIT 12
        """,
        (qvec, qvec, target),
    )
    print("\n3. EXACT SEARCH (index disabled)")
    found = False
    for cid, title, score, rank in cur.fetchall():
        hit = "  <-- TARGET" if cid.startswith(target + "#") else ""
        if hit:
            found = True
        print(f"   #{rank:<6} {score}  {cid[:44]:<46}{hit}")
    if not found:
        print(f"   >>> {target} did not surface at all — its embedding is far from the query.")

    # 4. does the HNSW index agree with exact search?
    cur.execute("SET LOCAL enable_indexscan = on")
    cur.execute(
        "SELECT chunk_id FROM chunks ORDER BY embedding <=> %s::vector LIMIT 5", (qvec,)
    )
    print("\n4. INDEX SEARCH (what 03_rag.py actually uses)")
    for (cid,) in cur.fetchall():
        print(f"   {cid}")
    print("\n   If 3 and 4 disagree, the HNSW index is the problem:")
    print("   try  SET hnsw.ef_search = 200;  or drop the index and use exact search.")
