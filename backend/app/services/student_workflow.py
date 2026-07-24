from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException

from app.config import (
    A2A_DLQ_AGENT_WEBHOOK_URL,
    A2A_GRADING_AGENT_WEBHOOK_URL,
    A2A_STUDENT_ORCHESTRATOR_WEBHOOK_URL,
)
from app.models import (
    AgentCardSearchRequest,
    AgentDispatchRequest,
    StudentExamSubmitRequest,
    StudentGradingCallbackRequest,
)
from app.services.supabase_admin import (
    _get_current_user,
    _get_or_create_profile,
    _json_request,
    _require_supabase_admin_config,
)
from app.config import SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _post_external_json(url: str, payload: dict) -> Any:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            body = response.read().decode("utf-8", errors="ignore")
            return json.loads(body) if body else {"status": "sent"}
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        raise HTTPException(
            status_code=502,
            detail=f"Student workflow HTTP {error.code}: {body or error.reason}",
        ) from error
    except URLError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Student workflow unreachable: {error.reason}",
        ) from error


def _question_text(question: dict) -> str:
    return (
        question.get("enonce")
        or question.get("prompt")
        or question.get("question")
        or question.get("title")
        or ""
    )


def _question_type(question: dict) -> str:
    return question.get("type") or question.get("question_type") or ""


def _question_points(question: dict) -> float:
    value = question.get("points", question.get("bareme", 0))
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _exam_questions(exam: dict) -> list[dict]:
    questions = exam.get("questions")
    return questions if isinstance(questions, list) else []


def _exam_max_score(exam: dict) -> float:
    explicit_total = exam.get("bareme_total") or exam.get("max_score")
    try:
        if explicit_total is not None:
            return float(explicit_total)
    except (TypeError, ValueError):
        pass
    return sum(_question_points(question) for question in _exam_questions(exam))


def _fetch_published_exam(exam_id: str) -> dict:
    rows = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/published_exams?id=eq.{quote(exam_id)}&"
            "status=eq.published&"
            "select=id,title,module,evaluation_type,target_study_level,status,exam,teacher_note,created_at,created_by"
        ),
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Published exam not found.")
    return rows[0]


def _exam_server_file_path(exam: dict) -> str:
    """Resolve the uploaded Agentic file path without asking an LLM to recreate it."""
    direct_path = str(exam.get("server_file_path") or exam.get("file_path") or "").strip()
    if direct_path:
        return direct_path

    knowledge_base_id = str(exam.get("knowledge_base_id") or "").strip()
    if not knowledge_base_id:
        return ""

    rows = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/documents?"
            f"knowledge_base_id=eq.{quote(knowledge_base_id)}&"
            "select=file_path&order=created_at.asc&limit=1"
        ),
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []
    return str(rows[0].get("file_path") or "").strip() if rows else ""


def submit_student_exam_attempt(access_token: str, payload: StudentExamSubmitRequest) -> dict:
    """Save the student answers before any Agentic/A2A workflow is called."""
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    if profile.get("role") != "student":
        raise HTTPException(status_code=403, detail="Only students can submit exams.")

    exam_record = _fetch_published_exam(payload.exam_id)
    exam = exam_record.get("exam") or {}
    questions = _exam_questions(exam)
    answers_by_number = {answer.question_number: answer.answer for answer in payload.answers}

    existing_attempts = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/exam_attempts?"
            f"exam_id=eq.{quote(payload.exam_id)}&student_id=eq.{quote(current_user['id'])}&"
            "select=id,exam_id,student_id,status,submitted_at,score,max_score,feedback_global,created_at&"
            "order=created_at.desc&limit=1"
        ),
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []
    if existing_attempts:
        return {
            "status": "already_submitted",
            "attempt_id": existing_attempts[0]["id"],
            "correlation_id": existing_attempts[0]["id"],
            "workflow_status": "already_submitted",
        }

    attempt_rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/exam_attempts?select=id,exam_id,student_id,status,started_at,submitted_at,score,max_score,feedback_global,created_at",
        method="POST",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Prefer": "return=representation",
        },
        payload={
            "exam_id": payload.exam_id,
            "student_id": current_user["id"],
            "status": "submitted",
            "submitted_at": _now_iso(),
            "max_score": _exam_max_score(exam),
        },
    )
    if not attempt_rows:
        raise HTTPException(status_code=500, detail="Exam attempt was not created.")

    attempt = attempt_rows[0]
    answer_rows = []
    for index, question in enumerate(questions, start=1):
        question_number = int(question.get("numero") or question.get("number") or index)
        answer_rows.append(
            {
                "attempt_id": attempt["id"],
                "question_number": question_number,
                "question_text": _question_text(question),
                "question_type": _question_type(question),
                "student_answer": answers_by_number.get(question_number, ""),
                "max_points": _question_points(question),
            }
        )

    if answer_rows:
        _json_request(
            f"{SUPABASE_URL}/rest/v1/exam_answers",
            method="POST",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "Prefer": "return=minimal",
            },
            payload=answer_rows,
        )

    file_path = _exam_server_file_path(exam)
    workflow_payload = {
        "correlation_id": attempt["id"],
        "attempt_id": attempt["id"],
        "task": "grade_student_exam",
        "file_path": file_path,
        "server_file_path": file_path,
    }
    result = {
        "status": "submitted",
        "attempt_id": attempt["id"],
        "correlation_id": attempt["id"],
        "workflow_payload": workflow_payload,
        "workflow_status": "not_configured",
    }
    if not A2A_STUDENT_ORCHESTRATOR_WEBHOOK_URL:
        return result

    try:
        result["workflow_response"] = _post_external_json(
            A2A_STUDENT_ORCHESTRATOR_WEBHOOK_URL,
            workflow_payload,
        )
        result["workflow_status"] = "launched"
    except HTTPException as error:
        result["workflow_status"] = "launch_failed"
        result["workflow_error"] = error.detail
    return result


def retry_student_exam_workflow(access_token: str, attempt_id: str) -> dict:
    """Relaunch grading for an existing submitted attempt without duplicating answers."""
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    if profile.get("role") != "student":
        raise HTTPException(status_code=403, detail="Only students can relaunch grading.")

    attempts = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/exam_attempts?"
            f"id=eq.{quote(attempt_id)}&student_id=eq.{quote(current_user['id'])}&"
            "select=id,exam_id,status&limit=1"
        ),
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []
    if not attempts:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    attempt = attempts[0]
    if attempt.get("status") == "graded":
        raise HTTPException(status_code=409, detail="This attempt is already graded.")
    if not A2A_STUDENT_ORCHESTRATOR_WEBHOOK_URL:
        raise HTTPException(status_code=503, detail="Student workflow is not configured.")

    exam_record = _fetch_published_exam(attempt["exam_id"])
    exam = exam_record.get("exam") or {}
    file_path = _exam_server_file_path(exam)
    workflow_payload = {
        "correlation_id": attempt["id"],
        "attempt_id": attempt["id"],
        "task": "grade_student_exam",
        "file_path": file_path,
        "server_file_path": file_path,
    }

    try:
        workflow_response = _post_external_json(
            A2A_STUDENT_ORCHESTRATOR_WEBHOOK_URL,
            workflow_payload,
        )
        return {
            "status": "submitted",
            "attempt_id": attempt["id"],
            "correlation_id": attempt["id"],
            "workflow_status": "launched",
            "workflow_response": workflow_response,
        }
    except HTTPException as error:
        return {
            "status": "submitted",
            "attempt_id": attempt["id"],
            "correlation_id": attempt["id"],
            "workflow_status": "launch_failed",
            "workflow_error": error.detail,
        }


def list_student_attempts(access_token: str) -> list[dict]:
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    if profile.get("role") != "student":
        raise HTTPException(status_code=403, detail="Only students can list their attempts.")

    attempts = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/exam_attempts?student_id=eq.{quote(current_user['id'])}&"
            "select=id,exam_id,student_id,status,submitted_at,graded_at,score,max_score,feedback_global,created_at&"
            "order=created_at.desc"
        ),
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []

    for attempt in attempts:
        attempt["correlation_id"] = attempt["id"]
        attempt["answers"] = _json_request(
            (
                f"{SUPABASE_URL}/rest/v1/exam_answers?attempt_id=eq.{quote(attempt['id'])}&"
                "select=question_number,question_text,question_type,student_answer,correct_answer,points_obtained,max_points,feedback&"
                "order=question_number.asc"
            ),
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            },
        ) or []

    return attempts


def get_attempt_payload(correlation_id: str) -> dict:
    _require_supabase_admin_config()

    encoded_id = quote(correlation_id)
    attempts = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/exam_attempts?id=eq.{encoded_id}&"
            "select=id,exam_id,student_id,status,score,max_score,feedback_global,created_at"
        ),
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []
    if not attempts:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    attempt = attempts[0]
    exam_record = _fetch_published_exam(attempt["exam_id"])
    answers = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/exam_answers?attempt_id=eq.{encoded_id}&"
            "select=id,question_number,question_text,question_type,student_answer,correct_answer,points_obtained,max_points,feedback&"
            "order=question_number.asc"
        ),
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []

    return {
        "correlation_id": attempt["id"],
        "attempt": attempt,
        "exam_record": exam_record,
        "exam": exam_record.get("exam") or {},
        "student_answers": answers,
    }


def search_agent_card(payload: AgentCardSearchRequest) -> dict:
    cards = [
        {
            "agent_id": "student-grading-agent",
            "name": "Agent correcteur etudiant",
            "status": "active" if A2A_GRADING_AGENT_WEBHOOK_URL else "missing_webhook",
            "capabilities": ["grade_student_exam", "use_rag_context", "return_structured_json"],
            "webhook_url": A2A_GRADING_AGENT_WEBHOOK_URL,
        },
        {
            "agent_id": "dlq-agent",
            "name": "Agent DLQ",
            "status": "active" if A2A_DLQ_AGENT_WEBHOOK_URL else "missing_webhook",
            "capabilities": ["save_dlq_event", "store_workflow_error"],
            "webhook_url": A2A_DLQ_AGENT_WEBHOOK_URL,
        },
    ]
    for card in cards:
        if payload.capability in card["capabilities"] and card["webhook_url"]:
            return {"found": True, "agent_card": card}
    return {"found": False, "agent_card": None}


def prepare_agent_dispatch(payload: AgentDispatchRequest) -> dict:
    agent = search_agent_card(AgentCardSearchRequest(capability=payload.capability))
    if not agent["found"]:
        raise HTTPException(status_code=404, detail=f"No agent found for capability: {payload.capability}")

    attempt_payload = get_attempt_payload(payload.correlation_id)
    return {
        "agent_card": agent["agent_card"],
        "webhook_url": agent["agent_card"]["webhook_url"],
        "payload": {
            "correlation_id": payload.correlation_id,
            "attempt_id": attempt_payload["attempt"]["id"],
            "exam": attempt_payload["exam"],
            "student_answers": attempt_payload["student_answers"],
            "rag_context": payload.rag_context,
        },
    }


def save_student_grading_result(payload: StudentGradingCallbackRequest) -> dict:
    _require_supabase_admin_config()

    encoded_id = quote(payload.correlation_id)
    attempt_rows = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/exam_attempts?id=eq.{encoded_id}&"
            "select=id,exam_id,student_id,status,score,max_score,feedback_global,created_at"
        ),
        method="PATCH",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Prefer": "return=representation",
        },
        payload={
            "status": "graded",
            "graded_at": _now_iso(),
            "score": payload.score,
            "max_score": payload.max_score,
            "feedback_global": payload.feedback_global or "",
        },
    )
    if not attempt_rows:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    for answer in payload.answers:
        question_number = answer.get("question_number") or answer.get("numero")
        if question_number is None:
            continue
        _json_request(
            (
                f"{SUPABASE_URL}/rest/v1/exam_answers?"
                f"attempt_id=eq.{encoded_id}&question_number=eq.{quote(str(question_number))}"
            ),
            method="PATCH",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "Prefer": "return=minimal",
            },
            payload={
                "correct_answer": answer.get("correct_answer") or answer.get("bonne_reponse") or "",
                "points_obtained": answer.get("points_obtained") or answer.get("points") or 0,
                "feedback": answer.get("feedback") or "",
            },
        )

    return {"status": "graded", "attempt": attempt_rows[0]}
