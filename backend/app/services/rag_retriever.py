import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL
from app.models import ExamGenerationRequest
from app.services.rag_indexer import create_google_embedding


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
        raise RuntimeError(body or error.reason) from error
    except URLError as error:
        raise RuntimeError(f"Supabase is unreachable: {error.reason}") from error


def _headers(prefer: str | None = None) -> dict:
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"


def build_retrieval_query(request: ExamGenerationRequest) -> str:
    # Cette requete represente la question de l'enseignant. C'est elle qui
    # permet de chercher les chunks pertinents dans document_chunks.
    return (
        f"Module: {request.module}. "
        f"Niveau: {request.study_level}. "
        f"Difficulte: {request.difficulty}. "
        f"Type d'evaluation: {request.evaluation_type}. "
        f"Type de questions: {request.question_type}. "
        f"Nombre de questions: {request.question_count}. "
        f"Objectifs pedagogiques: {request.learning_objectives}. "
        f"Contraintes: {request.constraints or ''}."
    )


def _match_document_chunks(
    knowledge_base_id: str,
    retrieval_query: str,
    match_count: int,
) -> list[dict]:
    query_embedding = create_google_embedding(retrieval_query)
    return _json_request(
        f"{SUPABASE_URL}/rest/v1/rpc/match_document_chunks",
        method="POST",
        headers=_headers(),
        payload={
            "query_embedding": _vector_literal(query_embedding),
            "match_knowledge_base_id": knowledge_base_id,
            "match_count": match_count,
        },
    ) or []


def _create_retrieval_session(knowledge_base_id: str, retrieval_query: str) -> dict:
    rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/retrieval_sessions?select=id,knowledge_base_id,purpose,retrieval_query,created_at",
        method="POST",
        headers=_headers("return=representation"),
        payload={
            "knowledge_base_id": knowledge_base_id,
            "purpose": "exam_generation",
            "retrieval_query": retrieval_query,
        },
    )
    if not rows:
        raise RuntimeError("Retrieval session could not be created in Supabase.")
    return rows[0]


def _insert_retrieval_context_chunks(retrieval_session_id: str, chunks: list[dict]) -> None:
    if not chunks:
        return

    rows = [
        {
            "retrieval_session_id": retrieval_session_id,
            "knowledge_base_id": chunk["knowledge_base_id"],
            "document_id": chunk["document_id"],
            "filename": chunk["filename"],
            "content": chunk["content"],
            "page_number": chunk.get("page_number"),
            "chunk_index": chunk["chunk_index"],
            "similarity_score": chunk.get("similarity", 0),
        }
        for chunk in chunks
    ]
    _json_request(
        f"{SUPABASE_URL}/rest/v1/retrieval_context_chunks",
        method="POST",
        headers=_headers("return=minimal"),
        payload=rows,
    )


def retrieve_relevant_chunks(
    knowledge_base_id: str,
    request: ExamGenerationRequest,
    match_count: int = 8,
) -> dict:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Missing Supabase config for RAG retrieval.")

    # RAG naif :
    # 1. convertir la demande enseignant en embedding
    # 2. chercher les top_k chunks dans document_chunks
    # 3. stocker ces chunks dans une session courte
    # 4. envoyer seulement retrieval_session_id au workflow
    retrieval_query = build_retrieval_query(request)
    chunks = _match_document_chunks(knowledge_base_id, retrieval_query, match_count)
    if not chunks:
        return {
            "retrieval_session_id": "",
            "retrieval_query": retrieval_query,
            "chunks": [],
        }

    session = _create_retrieval_session(knowledge_base_id, retrieval_query)
    _insert_retrieval_context_chunks(session["id"], chunks)

    return {
        "retrieval_session_id": session["id"],
        "retrieval_query": retrieval_query,
        "chunks": chunks,
    }
