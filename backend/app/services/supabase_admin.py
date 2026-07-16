import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException

from app.config import SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL
from app.models import AgendaItemRequest, CreateUserRequest, ExamVisibilityRequest, ProfileUpdateRequest, PublishExamRequest


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
        raise HTTPException(
            status_code=502,
            detail=f"Supabase is unreachable: {error.reason}",
        ) from error


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
        if matched_rows:
            return matched_rows

        # If legacy profile data is incomplete, still return the closest class match
        # instead of hiding all events behind an empty screen.
        return [
            row
            for row in rows
            if _normalize_level(row.get("target_study_level")) in {"licence2", "license2"}
        ]

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
        ]

    return rows


def publish_exam_as_staff(access_token: str, payload: PublishExamRequest) -> dict:
    _require_supabase_admin_config()

    current_user = _get_current_user(access_token)
    profile = _get_or_create_profile(current_user)
    if profile.get("role") not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers and admins can publish exams.")

    exam = payload.exam
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
            "status": "published",
            "exam": exam,
            "teacher_note": payload.teacher_note or "",
            "created_by": current_user["id"],
        },
    )

    if not rows:
        raise HTTPException(status_code=500, detail="Exam was not published.")
    return rows[0]


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
