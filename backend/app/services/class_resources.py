from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import HTTPException

from app.config import SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL
from app.services.supabase_admin import (
    _get_current_user,
    _get_or_create_profile,
    _json_request,
    _normalize_level,
    _require_supabase_admin_config,
)


RESOURCE_DIR = Path(__file__).resolve().parents[2] / "data" / "class_resources"
MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
RESOURCE_COLUMNS = (
    "id,title,description,target_study_level,filename,storage_name,"
    "content_type,size_bytes,status,created_by,created_at"
)


def _authenticated_profile(access_token: str) -> dict:
    _require_supabase_admin_config()
    current_user = _get_current_user(access_token)
    return _get_or_create_profile(current_user)


def _staff_profile(access_token: str) -> dict:
    profile = _authenticated_profile(access_token)
    if profile.get("role") not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers and admins can manage resources.")
    return profile


def _service_headers(prefer: str | None = None) -> dict:
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _public_resource(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "storage_name"}


def create_class_resource(
    access_token: str,
    title: str,
    description: str,
    target_study_level: str,
    filename: str,
    content: bytes,
) -> dict:
    profile = _staff_profile(access_token)
    clean_title = title.strip()
    clean_level = target_study_level.strip()
    suffix = Path(filename or "").suffix.lower()

    if not clean_title or not clean_level:
        raise HTTPException(status_code=422, detail="Title and target class are required.")
    if suffix not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="Only PDF and image files are accepted.")
    if not content:
        raise HTTPException(status_code=422, detail="The selected file is empty.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="The file exceeds the 20 MB limit.")

    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid4()}{suffix}"
    destination = RESOURCE_DIR / storage_name
    destination.write_bytes(content)

    try:
        rows = _json_request(
            f"{SUPABASE_URL}/rest/v1/class_resources?select={RESOURCE_COLUMNS}",
            headers=_service_headers("return=representation"),
            method="POST",
            payload={
                "title": clean_title,
                "description": description.strip(),
                "target_study_level": clean_level,
                "filename": Path(filename).name,
                "storage_name": storage_name,
                "content_type": ALLOWED_TYPES[suffix],
                "size_bytes": len(content),
                "status": "published",
                "created_by": profile["id"],
            },
        ) or []
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    if not rows:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="The resource metadata could not be saved.")
    return _public_resource(rows[0])


def list_class_resources(access_token: str) -> list[dict]:
    profile = _authenticated_profile(access_token)
    rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/class_resources?select={RESOURCE_COLUMNS}&order=created_at.desc",
        headers=_service_headers(),
    ) or []

    role = profile.get("role")
    if role == "student":
        level = _normalize_level(profile.get("study_level"))
        rows = [
            row for row in rows
            if row.get("status") == "published"
            and _normalize_level(row.get("target_study_level")) == level
        ]
    elif role == "teacher":
        rows = [row for row in rows if row.get("created_by") == profile.get("id")]
    elif role != "admin":
        raise HTTPException(status_code=403, detail="Resource access is not allowed.")

    return [_public_resource(row) for row in rows]


def get_class_resource_file(access_token: str, resource_id: str) -> tuple[Path, dict]:
    profile = _authenticated_profile(access_token)
    encoded_id = quote(resource_id.strip())
    rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/class_resources?id=eq.{encoded_id}&select={RESOURCE_COLUMNS}&limit=1",
        headers=_service_headers(),
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Resource not found.")

    row = rows[0]
    role = profile.get("role")
    if role == "student":
        allowed = (
            row.get("status") == "published"
            and _normalize_level(row.get("target_study_level"))
            == _normalize_level(profile.get("study_level"))
        )
    elif role == "teacher":
        allowed = row.get("created_by") == profile.get("id")
    else:
        allowed = role == "admin"
    if not allowed:
        raise HTTPException(status_code=403, detail="This resource is not available for your class.")

    path = (RESOURCE_DIR / row["storage_name"]).resolve()
    if RESOURCE_DIR.resolve() not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="The resource file is unavailable.")
    return path, row


def delete_class_resource(access_token: str, resource_id: str) -> dict:
    profile = _staff_profile(access_token)
    encoded_id = quote(resource_id.strip())
    rows = _json_request(
        f"{SUPABASE_URL}/rest/v1/class_resources?id=eq.{encoded_id}&select={RESOURCE_COLUMNS}&limit=1",
        headers=_service_headers(),
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Resource not found.")

    row = rows[0]
    if profile.get("role") != "admin" and row.get("created_by") != profile.get("id"):
        raise HTTPException(status_code=403, detail="You cannot delete this resource.")

    deleted = _json_request(
        f"{SUPABASE_URL}/rest/v1/class_resources?id=eq.{encoded_id}&select=id",
        headers=_service_headers("return=representation"),
        method="DELETE",
    ) or []
    if not deleted:
        raise HTTPException(status_code=404, detail="Resource not found.")

    (RESOURCE_DIR / row["storage_name"]).unlink(missing_ok=True)
    return {"status": "deleted", "id": resource_id}
