"""The web UI.

    uvicorn app:app --reload
    open http://127.0.0.1:8000

One endpoint. It returns exactly what ask() returns, and index.html renders
whatever is in there — so when you add reranking or query rewriting in a later
phase, the new steps appear in the UI without touching this file.
"""
import importlib

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# module name starts with a digit, so it needs importlib
rag = importlib.import_module("03_rag")

app = FastAPI(title="rag")


class Query(BaseModel):
    question: str
    k: int = 6
    answer: bool = True


@app.get("/", response_class=HTMLResponse)
def index():
    return open("web/index.html", encoding="utf-8").read()


@app.post("/api/ask")
def api_ask(q: Query):
    return rag.ask(q.question, k=q.k, answer=q.answer)
