import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException

from app.config import SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL
from app.models import (
    AgendaItemRequest,
    AgentTelemetryEventRequest,
    CreateUserRequest,
    ExamApprovalReviewRequest,
    ExamVisibilityRequest,
    ProfileUpdateRequest,
    PublishedExamUpdateRequest,
    PublishExamRequest,
)


def _require_supabase_admin_config() -> None:
    missing = []
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_ANON_KEY:
        missing.append("SUPABASE_ANON_KEY")
    if not SUPABASE_SERVICE_ROLE_KEY:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")

    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing backend Supabase config: {', '.join(missing)}",
        )


def _json_request(url: str, headers: dict, method: str = "GET", payload: dict | None = None) -> Any:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}

    for attempt in range(3):
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8", errors="ignore")
                return json.loads(body) if body else None
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="ignore")
            raise HTTPException(
                status_code=error.code,
                detail=body or error.reason,
            ) from error
        except URLError as error:
            reason = str(error.reason)
            is_dns_error = "getaddrinfo" in reason.lower() or "name resolution" in reason.lower()
            if is_dns_error and attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise HTTPException(
                status_code=502,
                detail=f"Supabase is unreachable: {error.reason}",
            ) from error


def _find_pedagogical_report(value: Any) -> dict | None:
    if isinstance(value, str):
        cleaned = value.replace("```json", "").replace("```", "").strip()
        try:
            value = json.loads(cleaned)
        except (TypeError, json.JSONDecodeError):
            return None
    if isinstance(value, list):
        for item in value:
            report = _find_pedagogical_report(item)
            if report:
                return report
        return None
    if not isinstance(value, dict):
        return None
    if value.get("analysis_type") in ["exam_audit", "student_analysis"] and value.get("correlation_id"):
        return value
    for item in value.values():
        report = _find_pedagogical_report(item)
        if report:
            return report
    return None


def save_pedagogical_report_if_present(payload: dict) -> bool:
    """Persist a final agent report when the optional history table exists."""
    report = _find_pedagogical_report(payload)
    if not report:
        return False

    # Approval must keep working even when the optional report-history table
    # has not been created yet.
    if report.get("analysis_type") == "exam_audit" and report.get("exam_id"):
        _attach_audit_report_to_exam(str(report["exam_id"]), report)

    row = {
        "correlation_id": report["correlation_id"],
        "analysis_type": report["analysis_type"],
        "study_level": report.get("study_level") or "Non renseigne",
        "academic_year": report.get("academic_year") or "Non renseignee",
        "exam_id": report.get("exam_id") or None,
        "status": report.get("status") or "COMPLETED",
        "decision": report.get("decision") or report.get("recommendation"),
        "report": report,
    }
    _json_request(
        f"{SUPABASE_URL}/rest/v1/pedagogical_reports?on_conflict=correlation_id",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        method="POST",
        payload=row,
    )
    return True


def _attach_audit_report_to_exam(exam_id: str, report: dict) -> None:
    """Attach the automated audit to the hidden exam awaiting admin review."""
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/published_exams?id=eq.{quote(exam_id)}&select=id,exam&limit=1",
        headers=headers,
    ) or []
    if not rows:
        return

    exam = dict(rows[0].get("exam") or {})
    approval = dict(exam.get("_approval") or {})
    approval.update({
        "status": "pending",
        "audit_status": "completed",
        "audit_report": report,
        "audit_completed_at": datetime.now(timezone.utc).isoformat(),
    })
    exam["_approval"] = approval
    _json_request(
        f"{SUPABASE_URL}/rest/v1/published_exams?id=eq.{quote(exam_id)}",
        method="PATCH",
        headers={**headers, "Prefer": "return=minimal"},
        payload={"exam": exam, "status": "hidden"},
    )


def save_agent_telemetry_event(payload: AgentTelemetryEventRequest) -> dict:
    """Store one independent quality evaluation produced by the harness."""
    _require_supabase_admin_config()

    quality = payload.quality
    row = {
        "event_type": payload.event_type,
        "correlation_id": payload.correlation_id or None,
        "workflow_name": payload.workflow_name,
        "agent_name": payload.agent_name,
        "success": payload.success,
        "latency_ms": payload.latency_ms,
        "accuracy": quality.accuracy,
        "faithfulness": quality.faithfulness,
        "hallucination_score": quality.hallucination_score,
        "instruction_following": quality.instruction_following,
        "answer_relevancy": quality.answer_relevancy,
        "quality_passed": payload.quality_passed,
        "problems": payload.problems,
        "evidence": payload.evidence,
        "metadata": payload.metadata,
    }
    rows = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/agent_evaluations?"
            "select=id,event_type,correlation_id,workflow_name,agent_name,success,"
            "latency_ms,accuracy,faithfulness,hallucination_score,instruction_following,"
            "answer_relevancy,quality_passed,problems,evidence,metadata,created_at"
        ),
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Prefer": "return=representation",
        },
        method="POST",
        payload=row,
    ) or []

    if not rows:
        raise HTTPException(status_code=500, detail="Telemetry event was not stored.")
    return {"status": "stored", "event": rows[0]}


def get_agent_telemetry_dashboard(access_token: str, period_days: int = 30) -> dict:
    """Aggregate independent agent evaluations for the admin dashboard."""
    _require_admin(access_token)

    if period_days not in {7, 30, 90, 365}:
        raise HTTPException(status_code=422, detail="period_days must be 7, 30, 90 or 365.")

    start_date = datetime.now(timezone.utc) - timedelta(days=period_days)
    rows = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/agent_evaluations?"
            "select=id,event_type,correlation_id,workflow_name,agent_name,success,latency_ms,"
            "accuracy,faithfulness,hallucination_score,instruction_following,answer_relevancy,"
            "quality_passed,problems,evidence,created_at&"
            f"created_at=gte.{quote(start_date.isoformat())}&order=created_at.desc&limit=500"
        ),
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []

    def average(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 1) if values else None

    def quality_score(row: dict) -> float:
        values = [
            float(row.get("accuracy") or 0),
            float(row.get("faithfulness") or 0),
            float(row.get("instruction_following") or 0),
            float(row.get("answer_relevancy") or 0),
            100 - float(row.get("hallucination_score") or 0),
        ]
        return round(sum(values) / len(values), 1)

    total = len(rows)
    successful = sum(1 for row in rows if row.get("success"))
    quality_passed = sum(1 for row in rows if row.get("quality_passed"))
    latencies = [float(row["latency_ms"]) for row in rows if row.get("latency_ms") is not None]
    all_problems = [
        str(problem)
        for row in rows
        for problem in (row.get("problems") or [])
        if str(problem).strip()
    ]

    agent_groups: dict[tuple[str, str], list[dict]] = {}
    daily_groups: dict[str, list[dict]] = {}
    for row in rows:
        key = (str(row.get("workflow_name") or "workflow"), str(row.get("agent_name") or "agent"))
        agent_groups.setdefault(key, []).append(row)
        day = str(row.get("created_at") or "")[:10]
        if day:
            daily_groups.setdefault(day, []).append(row)

    agents = []
    for (workflow_name, agent_name), events in agent_groups.items():
        event_latencies = [float(item["latency_ms"]) for item in events if item.get("latency_ms") is not None]
        agents.append(
            {
                "workflow_name": workflow_name,
                "agent_name": agent_name,
                "executions": len(events),
                "success_rate": round(100 * sum(1 for item in events if item.get("success")) / len(events), 1),
                "quality_pass_rate": round(
                    100 * sum(1 for item in events if item.get("quality_passed")) / len(events), 1
                ),
                "quality_score": average([quality_score(item) for item in events]),
                "accuracy": average([float(item.get("accuracy") or 0) for item in events]),
                "faithfulness": average([float(item.get("faithfulness") or 0) for item in events]),
                "hallucination_score": average(
                    [float(item.get("hallucination_score") or 0) for item in events]
                ),
                "instruction_following": average(
                    [float(item.get("instruction_following") or 0) for item in events]
                ),
                "answer_relevancy": average(
                    [float(item.get("answer_relevancy") or 0) for item in events]
                ),
                "average_latency_ms": average(event_latencies),
            }
        )
    agents.sort(key=lambda item: (-item["executions"], item["agent_name"]))

    daily_trend = []
    for day in sorted(daily_groups):
        events = daily_groups[day]
        daily_trend.append(
            {
                "date": day,
                "executions": len(events),
                "quality_score": average([quality_score(item) for item in events]),
                "quality_pass_rate": round(
                    100 * sum(1 for item in events if item.get("quality_passed")) / len(events), 1
                ),
            }
        )

    recent_events = []
    for row in rows[:12]:
        recent_events.append(
            {
                **row,
                "quality_score": quality_score(row),
            }
        )

    return {
        "period_days": period_days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_executions": total,
            "success_rate": round(100 * successful / total, 1) if total else 0,
            "quality_pass_rate": round(100 * quality_passed / total, 1) if total else 0,
            "quality_score": average([quality_score(row) for row in rows]),
            "accuracy": average([float(row.get("accuracy") or 0) for row in rows]),
            "faithfulness": average([float(row.get("faithfulness") or 0) for row in rows]),
            "hallucination_score": average(
                [float(row.get("hallucination_score") or 0) for row in rows]
            ),
            "instruction_following": average(
                [float(row.get("instruction_following") or 0) for row in rows]
            ),
            "answer_relevancy": average(
                [float(row.get("answer_relevancy") or 0) for row in rows]
            ),
            "average_latency_ms": average(latencies),
            "latency_sample_count": len(latencies),
            "issue_count": len(all_problems),
        },
        "agents": agents,
        "daily_trend": daily_trend[-14:],
        "recent_events": recent_events,
    }


def _require_knowledge_base_document(knowledge_base_id: str) -> str:
    """Return the Agentic server path and reject an incomplete knowledge base."""
    encoded_id = quote(str(knowledge_base_id).strip())
    rows = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/documents?"
            f"knowledge_base_id=eq.{encoded_id}&"
            "select=file_path&order=created_at.asc&limit=1"
        ),
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []
    file_path = str(rows[0].get("file_path") or "").strip() if rows else ""
    if not file_path or file_path.startswith("pending-file-server://"):
        raise HTTPException(
            status_code=422,
            detail="The selected knowledge base has no uploaded Agentic file.",
        )
    return file_path


def _get_current_user(access_token: str) -> dict:
    return _json_request(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {access_token}",
        },
    )


def get_current_user_from_token(access_token: str) -> dict:
    _require_supabase_admin_config()
    return _get_current_user(access_token)


def _normalize_level(value: str | None) -> str:
    return "".join((value or "").lower().split())


def _get_profile(user_id: str) -> dict:
    encoded_id = quote(user_id)
    rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{encoded_id}&select=id,full_name,role,study_level",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    )
    if not rows:
        raise HTTPException(status_code=403, detail="Profile not found for current user.")
    return rows[0]


def _get_or_create_profile(current_user: dict) -> dict:
    metadata = current_user.get("user_metadata") or {}
    metadata_role = metadata.get("role") or "student"
    if metadata_role not in ["student", "teacher", "admin"]:
        metadata_role = "student"
    metadata_study_level = metadata.get("study_level") if metadata_role == "student" else None

    try:
        profile = _get_profile(current_user["id"])
    except HTTPException as error:
        if error.detail != "Profile not found for current user.":
            raise
    else:
        should_patch = False
        patch_payload = {}

        if not profile.get("full_name") and (metadata.get("full_name") or current_user.get("email")):
            patch_payload["full_name"] = metadata.get("full_name") or current_user.get("email") or ""
            should_patch = True

        if profile.get("role") == "student" and metadata_study_level and not profile.get("study_level"):
            patch_payload["study_level"] = metadata_study_level
            should_patch = True

        if should_patch:
            encoded_id = quote(current_user["id"])
            rows = _json_request(
                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{encoded_id}&select=id,full_name,role,study_level",
                method="PATCH",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                    "Prefer": "return=representation",
                },
                payload=patch_payload,
            )
            if rows:
                return rows[0]

        return profile

    payload = {
        "id": current_user["id"],
        "full_name": metadata.get("full_name") or current_user.get("email") or "",
        "role": metadata_role,
        "study_level": metadata_study_level,
    }
    rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/profiles?select=id,full_name,role,study_level",
        method="POST",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Prefer": "return=representation,resolution=merge-duplicates",
        },
        payload=payload,
    )
    if not rows:
        raise HTTPException(status_code=500, detail="Profile could not be created for current user.")
    return rows[0]


def _get_profile_role(user_id: str) -> str:
    return _get_profile(user_id).get("role", "")


def _require_admin(access_token: str) -> dict:
    _require_supabase_admin_config()
    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    if profile.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only administration users can manage profiles.")
    return current_user


def require_admin_access(access_token: str) -> dict:
    """Public role guard used by admin-only API endpoints."""
    return _require_admin(access_token)


def create_user_as_admin(access_token: str, payload: CreateUserRequest) -> dict:
    _require_admin(access_token)

    created_user = _json_request(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        method="POST",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
        payload={
            "email": payload.email,
            "password": payload.password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": payload.full_name,
                "role": payload.role,
                "study_level": payload.study_level if payload.role == "student" else None,
            },
        },
    )

    role_label = "Teacher" if payload.role == "teacher" else "Student"
    return {
        "message": f"{role_label} account created.",
        "user": {
            "id": created_user["id"],
            "email": created_user["email"],
            "full_name": payload.full_name,
            "role": payload.role,
            "study_level": payload.study_level if payload.role == "student" else None,
        },
    }


def list_profiles_as_admin(access_token: str) -> list[dict]:
    _require_admin(access_token)

    return _json_request(
        f"{SUPABASE_URL}/rest/v1/profiles?select=id,full_name,role,study_level,created_at&order=created_at.desc",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []


def update_profile_as_admin(access_token: str, profile_id: str, payload: ProfileUpdateRequest) -> dict:
    _require_admin(access_token)

    rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{quote(profile_id)}&select=id,full_name,role,study_level,created_at",
        method="PATCH",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Prefer": "return=representation",
        },
        payload={
            "full_name": payload.full_name,
            "role": payload.role,
            "study_level": payload.study_level if payload.role == "student" else None,
        },
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return rows[0]


def delete_profile_as_admin(access_token: str, profile_id: str) -> dict:
    current_user = _require_admin(access_token)
    if profile_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")

    _json_request(
        f"{SUPABASE_URL}/auth/v1/admin/users/{quote(profile_id)}",
        method="DELETE",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    )
    return {"message": "Profile deleted."}


def list_agenda_for_user(access_token: str) -> list[dict]:
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)

    select = "id,title,description,target_study_level,evaluation_type,scheduled_at,created_at,created_by"
    url = f"{SUPABASE_URL}/rest/v1/agenda_items?select={select}&order=scheduled_at.asc"

    rows = _json_request(
        url,
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []

    if profile.get("role") == "student":
        metadata = current_user.get("user_metadata") or {}
        study_level = _normalize_level(profile.get("study_level") or metadata.get("study_level"))
        if not study_level:
            return []
        matched_rows = [
            row
            for row in rows
            if _normalize_level(row.get("target_study_level")) == study_level
        ]
        return matched_rows

    return rows


def create_agenda_as_staff(access_token: str, payload: AgendaItemRequest) -> dict:
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    if profile.get("role") not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers and admins can create agenda items.")

    rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/agenda_items?select=id,title,description,target_study_level,evaluation_type,scheduled_at,created_at,created_by",
        method="POST",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Prefer": "return=representation",
        },
        payload={
            "title": payload.title,
            "description": payload.description or "",
            "target_study_level": payload.target_study_level,
            "evaluation_type": payload.evaluation_type,
            "scheduled_at": payload.scheduled_at,
            "created_by": current_user["id"],
        },
    )

    if not rows:
        raise HTTPException(status_code=500, detail="Agenda item was not created.")
    return rows[0]


def _exam_title(exam: dict) -> str:
    module = exam.get("module") or exam.get("matiere") or "Examen"
    evaluation_type = exam.get("type_evaluation") or exam.get("evaluation_type") or "Evaluation"
    return f"{module} - {evaluation_type}"


def list_published_exams_for_user(access_token: str) -> list[dict]:
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)

    select = (
        "id,title,module,evaluation_type,target_study_level,status,exam,"
        "teacher_note,created_at,created_by"
    )
    query = f"{SUPABASE_URL}/rest/v1/published_exams?select={select}&order=created_at.desc"
    if profile.get("role") == "student":
        query = f"{SUPABASE_URL}/rest/v1/published_exams?select={select}&status=eq.published&order=created_at.desc"
    elif profile.get("role") == "teacher":
        query += f"&created_by=eq.{quote(current_user['id'])}"

    rows = _json_request(
        query,
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []

    if profile.get("role") == "student":
        metadata = current_user.get("user_metadata") or {}
        study_level = _normalize_level(profile.get("study_level") or metadata.get("study_level"))
        return [
            row
            for row in rows
            if _normalize_level(row.get("target_study_level")) == study_level
            and (row.get("exam") or {}).get("_approval", {}).get("status", "approved") == "approved"
        ]

    if profile.get("role") == "teacher":
        return [
            row
            for row in rows
            if not (row.get("exam") or {}).get("_approval")
            or (row.get("exam") or {}).get("_approval", {}).get("status") == "approved"
        ]

    return rows


def list_exam_results_for_staff(access_token: str, study_level: str = "") -> list[dict]:
    """Return read-only graded attempts visible to the current staff member."""
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    role = profile.get("role")
    if role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers and admins can view results.")

    exam_query = (
        f"{SUPABASE_URL}/rest/v1/published_exams?"
        "select=id,title,module,target_study_level,created_by,exam&order=created_at.desc"
    )
    if role == "teacher":
        exam_query += f"&created_by=eq.{quote(current_user['id'])}"
    if study_level.strip():
        exam_query += f"&target_study_level=eq.{quote(study_level.strip())}"

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    exams = _json_request(exam_query, headers=headers) or []
    if not exams:
        return []

    exams_by_id = {str(exam["id"]): exam for exam in exams}
    exam_ids = ",".join(exams_by_id)
    attempts = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/exam_attempts?"
            f"exam_id=in.({exam_ids})&status=eq.graded&"
            "select=id,exam_id,student_id,status,submitted_at,graded_at,score,max_score,feedback_global&"
            "order=graded_at.desc"
        ),
        headers=headers,
    ) or []
    if not attempts:
        return []

    student_ids = ",".join({str(attempt["student_id"]) for attempt in attempts})
    students = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/profiles?id=in.({student_ids})&"
            "select=id,full_name,study_level"
        ),
        headers=headers,
    ) or []
    students_by_id = {str(student["id"]): student for student in students}

    attempt_ids = ",".join(str(attempt["id"]) for attempt in attempts)
    answers = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/exam_answers?attempt_id=in.({attempt_ids})&"
            "select=attempt_id,question_number,question_text,question_type,student_answer,"
            "correct_answer,points_obtained,max_points,feedback&order=question_number.asc"
        ),
        headers=headers,
    ) or []
    answers_by_attempt: dict[str, list[dict]] = {}
    for answer in answers:
        answers_by_attempt.setdefault(str(answer["attempt_id"]), []).append(answer)

    results = []
    for attempt in attempts:
        exam = exams_by_id.get(str(attempt["exam_id"]), {})
        student = students_by_id.get(str(attempt["student_id"]), {})
        exam_data = exam.get("exam") or {}
        results.append(
            {
                **attempt,
                "exam_title": exam.get("title") or _exam_title(exam_data),
                "module": exam.get("module") or exam_data.get("module") or "Matiere non renseignee",
                "target_study_level": exam.get("target_study_level") or student.get("study_level") or "",
                "student_name": student.get("full_name") or "Etudiant",
                "student_study_level": student.get("study_level") or "",
                "answers": answers_by_attempt.get(str(attempt["id"]), []),
            }
        )

    return results


def get_dashboard_metrics_for_staff(
    access_token: str,
    study_level: str,
    academic_year: str,
) -> dict:
    """Aggregate anonymized class indicators for the staff dashboard."""
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    role = profile.get("role")
    if role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers and admins can view dashboard metrics.")

    match = re.fullmatch(r"(\d{4})-(\d{4})", academic_year.strip())
    if not match or int(match.group(2)) != int(match.group(1)) + 1:
        raise HTTPException(status_code=422, detail="academic_year must use the format YYYY-YYYY.")

    start_year = int(match.group(1))
    start_date = datetime(start_year, 9, 1, tzinfo=timezone.utc)
    end_date = datetime(start_year + 1, 9, 1, tzinfo=timezone.utc)
    level = study_level.strip()
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }

    students = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/profiles?role=eq.student&"
            f"study_level=eq.{quote(level)}&select=id"
        ),
        headers=headers,
    ) or []

    exam_query = (
        f"{SUPABASE_URL}/rest/v1/published_exams?"
        f"target_study_level=eq.{quote(level)}&select=id,title,module,created_by"
    )
    if role == "teacher":
        exam_query += f"&created_by=eq.{quote(current_user['id'])}"
    exams = _json_request(exam_query, headers=headers) or []
    exams_by_id = {str(exam["id"]): exam for exam in exams}

    results = list_exam_results_for_staff(access_token, level)
    filtered_results = []
    for result in results:
        raw_date = result.get("graded_at") or result.get("submitted_at")
        if not raw_date:
            continue
        result_date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        if start_date <= result_date < end_date:
            filtered_results.append(result)

    distribution = [
        {"label": "0-49 %", "count": 0},
        {"label": "50-69 %", "count": 0},
        {"label": "70-84 %", "count": 0},
        {"label": "85-100 %", "count": 0},
    ]
    exam_stats: dict[str, dict] = {}
    question_stats: dict[tuple[str, int], dict] = {}
    total_percent = 0.0

    for result in filtered_results:
        maximum = float(result.get("max_score") or 0)
        percent = 100 * float(result.get("score") or 0) / maximum if maximum > 0 else 0
        total_percent += percent
        bucket = 0 if percent < 50 else 1 if percent < 70 else 2 if percent < 85 else 3
        distribution[bucket]["count"] += 1

        exam_id = str(result.get("exam_id"))
        stat = exam_stats.setdefault(
            exam_id,
            {
                "exam_id": exam_id,
                "title": result.get("exam_title") or exams_by_id.get(exam_id, {}).get("title") or "Examen",
                "attempt_count": 0,
                "percent_total": 0.0,
            },
        )
        stat["attempt_count"] += 1
        stat["percent_total"] += percent

        for answer in result.get("answers") or []:
            key = (exam_id, int(answer.get("question_number") or 0))
            question = question_stats.setdefault(
                key,
                {
                    "exam_id": exam_id,
                    "question_number": key[1],
                    "question_text": answer.get("question_text") or "Question",
                    "points": 0.0,
                    "max_points": 0.0,
                    "responses_count": 0,
                },
            )
            question["points"] += float(answer.get("points_obtained") or 0)
            question["max_points"] += float(answer.get("max_points") or 0)
            question["responses_count"] += 1

    exam_performance = []
    for stat in exam_stats.values():
        attempts = stat.pop("attempt_count")
        total = stat.pop("percent_total")
        exam_performance.append({
            **stat,
            "attempt_count": attempts,
            "average_percent": round(total / attempts, 1) if attempts else 0,
        })
    exam_performance.sort(key=lambda item: item["average_percent"], reverse=True)

    difficult_questions = []
    for question in question_stats.values():
        maximum = question.pop("max_points")
        obtained = question.pop("points")
        question["success_rate"] = round(100 * obtained / maximum, 1) if maximum > 0 else 0
        difficult_questions.append(question)
    difficult_questions.sort(key=lambda item: item["success_rate"])

    attempt_count = len(filtered_results)
    possible_attempts = len(students) * len(exams)
    latest_report = None
    try:
        report_rows = _json_request(
            (
                f"{SUPABASE_URL}/rest/v1/pedagogical_reports?"
                "analysis_type=eq.student_analysis&"
                f"study_level=eq.{quote(level)}&academic_year=eq.{quote(academic_year)}&"
                "select=decision,status,report,created_at&order=created_at.desc&limit=1"
            ),
            headers=headers,
        ) or []
        latest_report = report_rows[0] if report_rows else None
    except HTTPException:
        # The dashboard remains usable before the optional history SQL is installed.
        latest_report = None

    return {
        "study_level": level,
        "academic_year": academic_year,
        "summary": {
            "student_count": len(students),
            "exam_count": len(exams),
            "graded_attempt_count": attempt_count,
            "class_average_percent": round(total_percent / attempt_count, 1) if attempt_count else 0,
            "participation_percent": round(100 * attempt_count / possible_attempts, 1) if possible_attempts else 0,
        },
        "grade_distribution": distribution,
        "exam_performance": exam_performance,
        "difficult_questions": difficult_questions[:5],
        "data_status": "READY" if attempt_count >= 5 else "INSUFFICIENT_DATA",
        "latest_report": latest_report,
    }


def publish_exam_as_staff(access_token: str, payload: PublishExamRequest) -> dict:
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    if profile.get("role") not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers and admins can publish exams.")

    exam = dict(payload.exam)
    knowledge_base_id = payload.knowledge_base_id or exam.get("knowledge_base_id")
    if not knowledge_base_id:
        raise HTTPException(status_code=422, detail="A knowledge base is required to publish an exam.")

    file_path = _require_knowledge_base_document(knowledge_base_id)
    exam["knowledge_base_id"] = str(knowledge_base_id)
    exam["file_path"] = file_path
    exam["server_file_path"] = file_path
    exam["_approval"] = {
        "status": "pending",
        "submitted_by": current_user["id"],
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "audit_status": "pending",
        "audit_report": None,
    }
    rows = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/published_exams?"
            "select=id,title,module,evaluation_type,target_study_level,status,exam,teacher_note,created_at,created_by"
        ),
        method="POST",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Prefer": "return=representation",
        },
        payload={
            "title": _exam_title(exam),
            "module": exam.get("module") or "",
            "evaluation_type": exam.get("type_evaluation") or exam.get("evaluation_type") or "",
            "target_study_level": payload.target_study_level,
            "status": "hidden",
            "exam": exam,
            "teacher_note": payload.teacher_note or "",
            "created_by": current_user["id"],
        },
    )

    if not rows:
        raise HTTPException(status_code=500, detail="Exam was not submitted for approval.")
    return rows[0]


def set_exam_audit_run(exam_id: str, run: dict | None = None, error: str = "") -> dict:
    """Store the workflow correlation or launch error on a pending exam."""
    _require_supabase_admin_config()
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/published_exams?id=eq.{quote(exam_id)}&select=id,exam&limit=1",
        headers=headers,
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Exam not found.")

    exam = dict(rows[0].get("exam") or {})
    approval = dict(exam.get("_approval") or {})
    approval["audit_status"] = "launched" if run else "launch_failed"
    approval["audit_correlation_id"] = (run or {}).get("correlation_id")
    approval["audit_error"] = error or None
    exam["_approval"] = approval
    updated = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/published_exams?id=eq.{quote(exam_id)}&"
            "select=id,title,module,evaluation_type,target_study_level,status,exam,teacher_note,created_at,created_by"
        ),
        method="PATCH",
        headers={**headers, "Prefer": "return=representation"},
        payload={"exam": exam, "status": "hidden"},
    ) or []
    return updated[0]


def review_exam_approval_as_admin(
    access_token: str,
    exam_id: str,
    payload: ExamApprovalReviewRequest,
) -> dict:
    """Approve or reject an exam without publishing it to students."""
    reviewer = _require_admin(access_token)
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/published_exams?id=eq.{quote(exam_id)}&select=id,exam&limit=1",
        headers=headers,
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Exam not found.")

    exam = dict(rows[0].get("exam") or {})
    approval = dict(exam.get("_approval") or {})
    approval.update({
        "status": "approved" if payload.decision == "approve" else "rejected",
        "reviewed_by": reviewer["id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_reason": (payload.reason or "").strip(),
    })
    exam["_approval"] = approval
    updated = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/published_exams?id=eq.{quote(exam_id)}&"
            "select=id,title,module,evaluation_type,target_study_level,status,exam,teacher_note,created_at,created_by"
        ),
        method="PATCH",
        headers={**headers, "Prefer": "return=representation"},
        payload={
            "exam": exam,
            # Administrative approval hands the exam back to the teacher.
            # Only the teacher's later publication action makes it visible.
            "status": "hidden",
        },
    ) or []
    return updated[0]


def delete_published_exam_as_staff(access_token: str, exam_id: str) -> dict:
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    if profile.get("role") not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers and admins can delete exams.")

    encoded_id = quote(exam_id)
    _json_request(
        f"{SUPABASE_URL}/rest/v1/published_exams?id=eq.{encoded_id}",
        method="DELETE",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    )
    return {"status": "deleted", "id": exam_id}


def update_published_exam_visibility_as_staff(
    access_token: str,
    exam_id: str,
    payload: ExamVisibilityRequest,
) -> dict:
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    if profile.get("role") not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers and admins can update exams.")

    encoded_id = quote(exam_id)
    current_rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/published_exams?id=eq.{encoded_id}&select=exam,created_by&limit=1",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    ) or []
    if not current_rows:
        raise HTTPException(status_code=404, detail="Exam not found.")

    current_exam = current_rows[0]
    approval_status = ((current_exam.get("exam") or {}).get("_approval") or {}).get("status")
    if payload.status == "published" and profile.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Only the teacher can publish an approved exam.")
    if profile.get("role") == "teacher" and current_exam.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Teachers can only manage their own exams.")
    if payload.status == "published" and approval_status not in [None, "approved"]:
        raise HTTPException(status_code=403, detail="Administrative approval is required before publication.")

    rows = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/published_exams?id=eq.{encoded_id}&"
            "select=id,title,module,evaluation_type,target_study_level,status,exam,teacher_note,created_at,created_by"
        ),
        method="PATCH",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Prefer": "return=representation",
        },
        payload={"status": payload.status},
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Exam not found.")
    return rows[0]


def update_published_exam_as_staff(
    access_token: str,
    exam_id: str,
    payload: PublishedExamUpdateRequest,
) -> dict:
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    if profile.get("role") not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers and admins can update exams.")

    exam = dict(payload.exam)
    knowledge_base_id = payload.knowledge_base_id or exam.get("knowledge_base_id")
    if not knowledge_base_id:
        raise HTTPException(status_code=422, detail="A knowledge base is required to update an exam.")

    file_path = _require_knowledge_base_document(knowledge_base_id)
    exam["knowledge_base_id"] = str(knowledge_base_id)
    exam["file_path"] = file_path
    exam["server_file_path"] = file_path
    encoded_id = quote(exam_id)
    rows = _json_request(
        (
            f"{SUPABASE_URL}/rest/v1/published_exams?id=eq.{encoded_id}&"
            "select=id,title,module,evaluation_type,target_study_level,status,exam,teacher_note,created_at,created_by"
        ),
        method="PATCH",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Prefer": "return=representation",
        },
        payload={
            "title": _exam_title(exam),
            "module": exam.get("module") or "",
            "evaluation_type": exam.get("type_evaluation") or exam.get("evaluation_type") or "",
            "target_study_level": payload.target_study_level or exam.get("niveau") or exam.get("study_level") or "",
            "exam": exam,
            "teacher_note": payload.teacher_note or "",
        },
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Exam not found.")
    return rows[0]
