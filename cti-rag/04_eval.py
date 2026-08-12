"""4. Score retrieval against questions.yaml.

    python 04_eval.py

Without this you are tuning on vibes. Every later phase (better parsing, better
chunking, hybrid search, reranking) is justified or rejected by this number.

recall@k — of the documents that should have been found, how many were in top-k.
           This is the CEILING on answer quality: what retrieval misses, the
           model invents.
hit@k    — did at least one correct document make it in.
mrr      — how high the first correct one ranked.
"""
import importlib
import json
from collections import defaultdict

import yaml

rag = importlib.import_module("03_rag")

QUESTIONS = "questions.yaml"
KS = (1, 5, 10, 20)


def doc_ids(question, k):
    """Chunk hits collapse to unique doc_ids — labels are doc-level.
    Over-fetch 3x so k chunks from one document don't crowd out the rest."""
    seen, out = set(), []
    for e in rag.search(question, k=k * 3):
        if e["doc_id"] not in seen:
            seen.add(e["doc_id"])
            out.append(e["doc_id"])
        if len(out) >= k:
            break
    return out


def main():
    questions = yaml.safe_load(open(QUESTIONS, encoding="utf-8"))
    scored = [q for q in questions
              if q.get("type") != "unanswerable" and q.get("relevant_doc_ids")]
    print(f"scoring {len(scored)} of {len(questions)} questions "
          f"(unanswerable + unlabeled are skipped)\n")

    agg = defaultdict(list)
    by_type = defaultdict(lambda: defaultdict(list))
    worst = []

    for q in scored:
        got = doc_ids(q["question"], max(KS))
        rel = set(q["relevant_doc_ids"])

        for k in KS:
            top = set(got[:k])
            recall = len(top & rel) / len(rel)
            agg[f"recall@{k}"].append(recall)
            agg[f"hit@{k}"].append(1.0 if top & rel else 0.0)
            by_type[q["type"]][f"recall@{k}"].append(recall)

        rr = next((1 / i for i, d in enumerate(got, 1) if d in rel), 0.0)
        agg["mrr"].append(rr)
        by_type[q["type"]]["mrr"].append(rr)
        worst.append((len(set(got) & rel) / len(rel), q["id"], q["question"]))

    avg = lambda v: round(sum(v) / len(v), 3)

    print("OVERALL")
    for k in sorted(agg):
        print(f"  {k:<12} {avg(agg[k])}")

    print("\nBY TYPE")
    for t in sorted(by_type):
        line = "  ".join(f"{k}={avg(v)}" for k, v in sorted(by_type[t].items()))
        print(f"  {t:<12} {line}")

    print("\nWORST (fix these first)")
    for score, qid, text in sorted(worst)[:5]:
        print(f"  [{score:.2f}] {qid}  {text[:70]}")

    result = {"overall": {k: avg(v) for k, v in agg.items()},
              "by_type": {t: {k: avg(v) for k, v in d.items()}
                          for t, d in by_type.items()}}
    json.dump(result, open("eval_results.json", "w"), indent=2)
    print("\nsaved eval_results.json")


if __name__ == "__main__":
    main()
