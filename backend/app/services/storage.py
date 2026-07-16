import json
from typing import Any, List
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import UploadFile

from app.config import AGENTIC_FILE_SERVER_ENABLED, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL
from app.models import KnowledgeBase, KnowledgeBaseDocument
from app.services.agentic_file_server import upload_to_agentic_file_server

BASE_DIR = Path(__file__).resolve().parents[2]
LAST_WORKFLOW_RESULT_FILE = BASE_DIR / "data" / "last_workflow_result.json"


def _require_supabase_storage_config() -> None:
    missing = []
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_ANON_KEY:
        missing.append("SUPABASE_ANON_KEY")
    if not SUPABASE_SERVICE_ROLE_KEY:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise RuntimeError(f"Missing Supabase storage config: {', '.join(missing)}")


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
    _require_supabase_storage_config()
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def load_knowledge_bases() -> List[KnowledgeBase]:
    kb_rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/knowledge_bases?select=id,name,subject,created_at&order=created_at.desc",
        headers=_headers(),
    ) or []
    doc_rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/documents?select=id,knowledge_base_id,filename,file_path,content_type,size_bytes,created_at&order=created_at.asc",
        headers=_headers(),
    ) or []

    documents_by_kb: dict[str, list[KnowledgeBaseDocument]] = {}
    for row in doc_rows:
        documents_by_kb.setdefault(row["knowledge_base_id"], []).append(
            KnowledgeBaseDocument(
                id=row["id"],
                filename=row["filename"],
                file_path=row.get("file_path") or "",
                content_type=row.get("content_type") or "application/octet-stream",
                size_bytes=row.get("size_bytes") or 0,
            )
        )

    return [
        KnowledgeBase(
            id=row["id"],
            name=row["name"],
            subject=row["subject"],
            created_at=row["created_at"],
            documents=documents_by_kb.get(row["id"], []),
        )
        for row in kb_rows
    ]


def get_knowledge_base(kb_id: str) -> KnowledgeBase | None:
    encoded_id = quote(kb_id)
    kb_rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/knowledge_bases?id=eq.{encoded_id}&select=id,name,subject,created_at",
        headers=_headers(),
    ) or []
    if not kb_rows:
        return None

    doc_rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/documents?knowledge_base_id=eq.{encoded_id}&select=id,knowledge_base_id,filename,file_path,content_type,size_bytes,created_at&order=created_at.asc",
        headers=_headers(),
    ) or []
    documents = [
        KnowledgeBaseDocument(
            id=row["id"],
            filename=row["filename"],
            file_path=row.get("file_path") or "",
            content_type=row.get("content_type") or "application/octet-stream",
            size_bytes=row.get("size_bytes") or 0,
        )
        for row in doc_rows
    ]
    row = kb_rows[0]
    return KnowledgeBase(
        id=row["id"],
        name=row["name"],
        subject=row["subject"],
        created_at=row["created_at"],
        documents=documents,
    )


def delete_knowledge_base(kb_id: str) -> None:
    encoded_id = quote(kb_id)
    _json_request(
        f"{SUPABASE_URL}/rest/v1/retrieval_context_chunks?knowledge_base_id=eq.{encoded_id}",
        method="DELETE",
        headers=_headers(),
    )
    _json_request(
        f"{SUPABASE_URL}/rest/v1/retrieval_sessions?knowledge_base_id=eq.{encoded_id}",
        method="DELETE",
        headers=_headers(),
    )
    _json_request(
        f"{SUPABASE_URL}/rest/v1/document_chunks?knowledge_base_id=eq.{encoded_id}",
        method="DELETE",
        headers=_headers(),
    )
    _json_request(
        f"{SUPABASE_URL}/rest/v1/documents?knowledge_base_id=eq.{encoded_id}",
        method="DELETE",
        headers=_headers(),
    )
    _json_request(
        f"{SUPABASE_URL}/rest/v1/knowledge_bases?id=eq.{encoded_id}",
        method="DELETE",
        headers=_headers(),
    )


def save_uploaded_files(
    kb: KnowledgeBase,
    files: List[UploadFile],
    owner_id: str,
) -> tuple[KnowledgeBase, list[tuple[KnowledgeBaseDocument, bytes]]]:
    kb_rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/knowledge_bases?select=id,name,subject,created_at",
        method="POST",
        headers=_headers("return=representation"),
        payload={
            "id": kb.id,
            "owner_id": owner_id,
            "name": kb.name,
            "subject": kb.subject,
        },
    )
    if not kb_rows:
        raise RuntimeError("Knowledge base could not be created in Supabase.")

    uploaded_documents: list[tuple[KnowledgeBaseDocument, bytes]] = []
    for file in files:
        safe_name = (file.filename or "document").split("/")[-1].split("\\")[-1]
        content = file.file.read()
        content_type = file.content_type or "application/octet-stream"
        if AGENTIC_FILE_SERVER_ENABLED:
            # POC Read File :
            # Le fichier doit exister sur le serveur de la plateforme agentic.
            # Le chemin retourne ici est celui que le noeud Read File doit recevoir.
            file_path = upload_to_agentic_file_server(safe_name, content, content_type)
        else:
            file_path = f"pending-file-server://documents/{kb.id}/{safe_name}"

        document = KnowledgeBaseDocument(
            filename=safe_name,
            file_path=file_path,
            content_type=content_type,
            size_bytes=len(content),
        )
        doc_rows = _json_request(
            f"{SUPABASE_URL}/rest/v1/documents?select=id,knowledge_base_id,filename,file_path,content_type,size_bytes,created_at",
            method="POST",
            headers=_headers("return=representation"),
            payload={
                "id": document.id,
                "knowledge_base_id": kb.id,
                "filename": document.filename,
                "file_path": document.file_path,
                "content_type": document.content_type,
                "size_bytes": document.size_bytes,
            },
        )
        if not doc_rows:
            raise RuntimeError(f"Document {safe_name} could not be created in Supabase.")
        kb.documents.append(document)
        uploaded_documents.append((document, content))

    return kb, uploaded_documents


def save_last_workflow_result(payload: dict) -> dict:
    LAST_WORKFLOW_RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_WORKFLOW_RESULT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"status": "stored", "path": str(LAST_WORKFLOW_RESULT_FILE)}


def load_last_workflow_result() -> dict | None:
    if not LAST_WORKFLOW_RESULT_FILE.exists():
        return None
    return json.loads(LAST_WORKFLOW_RESULT_FILE.read_text(encoding="utf-8"))


def clear_last_workflow_result() -> dict:
    if LAST_WORKFLOW_RESULT_FILE.exists():
        LAST_WORKFLOW_RESULT_FILE.unlink()
    return {"status": "cleared"}
