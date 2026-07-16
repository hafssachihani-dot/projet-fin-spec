import json
import mimetypes
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import (
    AGENTIC_API_KEY,
    AGENTIC_FILE_UPLOAD_FIELD,
    AGENTIC_FILE_UPLOAD_TOKEN,
    AGENTIC_FILE_UPLOAD_URL,
)


def _require_file_server_config() -> None:
    missing = []
    if not AGENTIC_FILE_UPLOAD_URL:
        missing.append("AGENTIC_FILE_UPLOAD_URL")
    if not AGENTIC_API_KEY and not AGENTIC_FILE_UPLOAD_TOKEN:
        missing.append("AGENTIC_API_KEY or AGENTIC_FILE_UPLOAD_TOKEN")
    if missing:
        raise RuntimeError(
            "Missing file server config: "
            + ", ".join(missing)
            + ". Add your Agentic API key, and ask the platform team for the file upload API URL."
        )


def _multipart_body(field_name: str, filename: str, content: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = f"----codex-file-upload-{uuid.uuid4().hex}"
    lines = [
        f"--{boundary}",
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"',
        f"Content-Type: {content_type}",
        "",
        "",
    ]
    body = "\r\n".join(lines).encode("utf-8")
    body += content
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")
    return body, boundary


def _extract_file_path(response_payload: dict) -> str:
    # Les plateformes utilisent souvent un de ces noms.
    for key in ["file_path", "server_file_path", "path", "url", "id"]:
        value = response_payload.get(key)
        if isinstance(value, str) and value:
            return value

    data = response_payload.get("data")
    if isinstance(data, dict):
        return _extract_file_path(data)

    files = response_payload.get("files")
    if isinstance(files, list) and files and isinstance(files[0], dict):
        return _extract_file_path(files[0])

    raise RuntimeError(
        "File server upload succeeded, but no file_path/path/id was found in the response."
    )


def _auth_headers() -> dict:
    headers = {}

    # Si on a un token separe, il est prioritaire comme Bearer token.
    if AGENTIC_FILE_UPLOAD_TOKEN:
        headers["Authorization"] = f"Bearer {AGENTIC_FILE_UPLOAD_TOKEN}"

    # Le bundle officiel Agentic montre que les appels API utilisent x-api-key.
    if AGENTIC_API_KEY:
        headers["x-api-key"] = AGENTIC_API_KEY

    return headers


def upload_to_agentic_file_server(filename: str, content: bytes, content_type: str | None = None) -> str:
    _require_file_server_config()

    safe_content_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    body, boundary = _multipart_body(AGENTIC_FILE_UPLOAD_FIELD or "file", filename, content, safe_content_type)
    headers = {
        **_auth_headers(),
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    request = Request(
        AGENTIC_FILE_UPLOAD_URL,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            raw_body = response.read().decode("utf-8", errors="ignore")
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"File server upload HTTP {error.code} at {AGENTIC_FILE_UPLOAD_URL}: "
            f"{error_body or error.reason}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"File server upload unreachable: {error.reason}") from error

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"File server response is not JSON: {raw_body[:500]}") from error

    return _extract_file_path(payload)
