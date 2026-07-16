import json
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from app.config import AGENTIC_WEBHOOK_URL
from app.models import ExamGenerationRequest, KnowledgeBase


def build_workflow_payload(
    request: ExamGenerationRequest,
    kb: KnowledgeBase,
    retrieval_session_id: str = "",
) -> dict:
    first_document = kb.documents[0] if kb.documents else None
    file_path = first_document.file_path if first_document else ""

    exam_prompt = (
        f"Generate and quality-check an academic exam for module '{request.module}'. "
        f"Duration: {request.duration}. Study level: {request.study_level}. "
        f"Difficulty: {request.difficulty}. Evaluation type: {request.evaluation_type}. "
        f"Number of questions: {request.question_count}. "
        f"Learning objectives: {request.learning_objectives}. "
        f"Constraints: {request.constraints}."
    )

    # POC File Server :
    # Le workflow recoit seulement la demande d'examen + le chemin serveur du PDF.
    # Le noeud Read File doit utiliser file_path/server_file_path pour lire le PDF,
    # puis la plateforme fait Split + Embedding + RAG dans le workflow.
    return {
        "input_value": exam_prompt,
        "input_type": "chat",
        "output_type": "chat",
        "file_path": file_path,
        "server_file_path": file_path,
        "exam_request": request.model_dump(mode="json"),
    }


def _parse_response(body: str) -> Any:
    if not body:
        return {"message": "Workflow returned an empty response."}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"text": body}


def call_agentic_workflow(
    request: ExamGenerationRequest,
    kb: KnowledgeBase,
    retrieval_session_id: str = "",
) -> dict:
    if not AGENTIC_WEBHOOK_URL:
        raise ValueError("AGENTIC_WEBHOOK_URL is not configured in backend/.env")

    payload = build_workflow_payload(
        request,
        kb,
        retrieval_session_id=retrieval_session_id,
    )
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = Request(
        AGENTIC_WEBHOOK_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    run_id = str(uuid4())
    started_at = datetime.utcnow().isoformat() + "Z"

    try:
        with urlopen(http_request, timeout=120) as response:
            response_body = response.read().decode("utf-8", errors="ignore")
            return {
                "run_id": run_id,
                "status": "success",
                "started_at": started_at,
                "finished_at": datetime.utcnow().isoformat() + "Z",
                "webhook_url": AGENTIC_WEBHOOK_URL,
                "sent_payload": payload,
                "workflow_response": _parse_response(response_body),
            }
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Workflow HTTP {error.code}: {error_body or error.reason}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Workflow unreachable: {error.reason}") from error
