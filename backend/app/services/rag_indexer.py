import json
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import (
    GOOGLE_API_KEY,
    GOOGLE_EMBEDDING_DIMENSIONS,
    GOOGLE_EMBEDDING_MODEL,
    SUPABASE_ANON_KEY,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
)
from app.models import KnowledgeBase, KnowledgeBaseDocument


CHUNK_SIZE = 1200
CHUNK_OVERLAP = 180
DEFAULT_GOOGLE_EMBEDDING_MODEL = "models/gemini-embedding-001"


class ApiRequestError(RuntimeError):
    def __init__(self, status_code: int, body: str):
        super().__init__(body)
        self.status_code = status_code
        self.body = body


def _require_rag_config() -> None:
    missing = []
    if not GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_ANON_KEY:
        missing.append("SUPABASE_ANON_KEY")
    if not SUPABASE_SERVICE_ROLE_KEY:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise RuntimeError(f"Missing RAG config: {', '.join(missing)}")


def _json_request(url: str, headers: dict, method: str = "GET", payload: dict | None = None) -> Any:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8", errors="ignore")
            return json.loads(body) if body else None
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        raise ApiRequestError(error.code, body or str(error.reason)) from error
    except URLError as error:
        raise RuntimeError(f"External API is unreachable: {error.reason}") from error


def _extract_pdf_pages(file_content: bytes) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("Install backend dependency pypdf: pip install -r requirements.txt") from error

    reader = PdfReader(BytesIO(file_content))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({"page_number": index, "text": text})
    return pages


def _extract_text_pages(document: KnowledgeBaseDocument, file_content: bytes) -> list[dict]:
    suffix = Path(document.filename).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_pages(file_content)

    text = file_content.decode("utf-8", errors="ignore")
    return [{"page_number": None, "text": text}]


def _split_text(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(start + CHUNK_SIZE, len(cleaned))
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(cleaned):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return chunks


def _normalise_google_model(model: str) -> str:
    if not model.startswith("models/"):
        model = f"models/{model}"
    return model


def _google_embedding_payload(model: str, text: str) -> dict:
    return {
        "model": model,
        "content": {
            "parts": [{"text": text}],
        },
        "outputDimensionality": GOOGLE_EMBEDDING_DIMENSIONS,
    }


def _request_google_embedding(model: str, text: str) -> list[float]:
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:embedContent?key={GOOGLE_API_KEY}"
    response = _json_request(
        url,
        method="POST",
        headers={},
        payload=_google_embedding_payload(model, text),
    )
    values = response.get("embedding", {}).get("values") if response else None
    if not values:
        raise RuntimeError("Google embedding API returned no embedding values.")
    return values


def create_google_embedding(text: str) -> list[float]:
    _require_rag_config()
    model = _normalise_google_model(GOOGLE_EMBEDDING_MODEL)

    try:
        return _request_google_embedding(model, text)
    except ApiRequestError as error:
        if error.status_code != 404 or model == DEFAULT_GOOGLE_EMBEDDING_MODEL:
            raise

    return _request_google_embedding(DEFAULT_GOOGLE_EMBEDDING_MODEL, text)


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"


def _delete_existing_document_chunks(knowledge_base_id: str) -> None:
    _json_request(
        f"{SUPABASE_URL}/rest/v1/document_chunks?knowledge_base_id=eq.{knowledge_base_id}",
        method="DELETE",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    )


def _insert_document_chunks(rows: list[dict]) -> None:
    if not rows:
        return

    _json_request(
        f"{SUPABASE_URL}/rest/v1/document_chunks",
        method="POST",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Prefer": "return=minimal",
        },
        payload=rows,
    )


def index_uploaded_documents(
    kb: KnowledgeBase,
    uploaded_documents: list[tuple[KnowledgeBaseDocument, bytes]],
) -> dict:
    _require_rag_config()

    # RAG naif comme ChromaDB :
    # 1. lire le PDF
    # 2. decouper en chunks
    # 3. creer un embedding pour chaque chunk
    # 4. stocker tous les chunks dans document_chunks
    _delete_existing_document_chunks(kb.id)

    rows = []
    chunk_index = 0
    indexed_documents = []

    for document, file_content in uploaded_documents:
        document_chunk_count = 0
        for page in _extract_text_pages(document, file_content):
            for chunk in _split_text(page["text"]):
                embedding = create_google_embedding(chunk)
                rows.append(
                    {
                        "knowledge_base_id": kb.id,
                        "document_id": document.id,
                        "filename": document.filename,
                        "content": chunk,
                        "page_number": page["page_number"],
                        "chunk_index": chunk_index,
                        "embedding": _vector_literal(embedding),
                    }
                )
                chunk_index += 1
                document_chunk_count += 1

        indexed_documents.append(
            {
                "document_id": document.id,
                "filename": document.filename,
                "chunk_count": document_chunk_count,
            }
        )

    if not rows:
        raise RuntimeError("No readable text was found in the uploaded documents.")

    _insert_document_chunks(rows)
    return {
        "knowledge_base_id": kb.id,
        "document_count": len(uploaded_documents),
        "chunk_count": len(rows),
        "documents": indexed_documents,
    }
