"""1. Turn the PDFs in data/pdfs/ into data/corpus/reports.jsonl

Same shape as your attack/cisa/kev jsonl files, so everything downstream treats
them identically:
    {"doc_id", "source", "title", "text", "url", "published", "metadata"}

Extraction here is deliberately naive (plain PyMuPDF text). Tables come out
mangled. That is the baseline Phase 2 improves on — don't fix it yet.

    python 01_pdfs_to_jsonl.py
"""
import json
import os
import re

import pymupdf

import config


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def main():
    os.makedirs(config.CORPUS_DIR, exist_ok=True)
    pdfs = sorted(f for f in os.listdir(config.PDF_DIR) if f.lower().endswith(".pdf"))
    if not pdfs:
        print(f"no PDFs found in {config.PDF_DIR}/")
        return

    out_path = os.path.join(config.CORPUS_DIR, "reports.jsonl")
    n = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for fname in pdfs:
            path = os.path.join(config.PDF_DIR, fname)
            with pymupdf.open(path) as pdf:
                pages = [p.get_text() for p in pdf]
            text = "\n\n".join(pages).strip()

            if len(text) < 500:
                print(f"  WARNING {fname}: only {len(text)} chars — "
                      f"probably a scanned PDF, needs OCR (Phase 2)")

            doc = {
                "doc_id": f"report:{slug(os.path.splitext(fname)[0])}",
                "source": "report",
                "title": os.path.splitext(fname)[0],
                "text": text,
                "url": None,
                "published": None,
                "metadata": {"filename": fname, "pages": len(pages),
                             "extractor": "pymupdf-plain"},
            }
            out.write(json.dumps(doc, ensure_ascii=False) + "\n")
            n += 1
            print(f"  {fname}: {len(pages)} pages, {len(text):,} chars")

    print(f"\nwrote {n} documents -> {out_path}")


if __name__ == "__main__":
    main()
