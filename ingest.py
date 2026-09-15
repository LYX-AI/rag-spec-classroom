"""Slice spec sheets, embed with SiliconFlow BAAI/bge-m3, store vectors locally.

Chat still uses Zhipu glm-4-flash in bedrock_utils.py.
Replaces: S3 upload + Bedrock Knowledge Base ingest + Aurora pgvector.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
SHEETS = ROOT / "scripts" / "spec-sheets"
INDEX_DIR = ROOT / "data" / "index"
CHUNKS_PATH = INDEX_DIR / "chunks.json"
VECTORS_PATH = INDEX_DIR / "vectors.npy"

load_dotenv(ROOT / ".env")


def _embed_client() -> OpenAI:
    key = os.getenv("SILICONFLOW_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Set SILICONFLOW_API_KEY in .env (SiliconFlow, free BAAI/bge-m3).")
    return OpenAI(api_key=key, base_url="https://api.siliconflow.cn/v1")


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages)


def read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return read_pdf(path)
    return path.read_text(encoding="utf-8")


def list_source_files() -> list[Path]:
    pdfs = sorted(SHEETS.glob("*.pdf"))
    if pdfs:
        return pdfs
    return sorted(SHEETS.glob("*.md"))


def chunk_text(text: str, size: int = 500, overlap: int = 80) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(text) <= size:
        return [text] if text else []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def embed_texts(texts: list[str]) -> np.ndarray:
    client = _embed_client()
    vectors = []
    batch = 16
    for i in range(0, len(texts), batch):
        part = texts[i : i + batch]
        resp = client.embeddings.create(model="BAAI/bge-m3", input=part)
        ordered = sorted(resp.data, key=lambda x: getattr(x, "index", 0))
        vectors.extend([row.embedding for row in ordered])
    arr = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-8, None)
    return arr / norms


def ingest() -> int:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    sources = list_source_files()
    for path in sources:
        raw = read_document(path)
        for i, chunk in enumerate(chunk_text(raw)):
            records.append({"id": f"{path.stem}-{i}", "source": path.name, "text": chunk})
    if not records:
        raise RuntimeError(f"No spec sheets in {SHEETS}")
    vectors = embed_texts([r["text"] for r in records])
    CHUNKS_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    np.save(VECTORS_PATH, vectors)
    return len(records)


def load_index() -> tuple[list[dict], np.ndarray]:
    if not CHUNKS_PATH.exists() or not VECTORS_PATH.exists():
        ingest()
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    vectors = np.load(VECTORS_PATH)
    return chunks, vectors


def search(query: str, top_k: int = 3) -> list[dict]:
    chunks, vectors = load_index()
    q = embed_texts([query])[0]
    scores = vectors @ q
    k = min(top_k, len(chunks))
    idxs = np.argsort(-scores)[:k]
    results = []
    for idx in idxs:
        item = chunks[int(idx)]
        results.append(
            {
                "text": item["text"],
                "score": float(scores[int(idx)]),
                "metadata": {"id": item["id"]},
                "source": item["source"],
                "location": {"type": "LOCAL", "path": item["source"]},
            }
        )
    return results


if __name__ == "__main__":
    n = ingest()
    print(f"ingested {n} chunks into {INDEX_DIR}")
