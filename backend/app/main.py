import json
import secrets
from datetime import datetime
from typing import List

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.config import TELEMETRY_API_KEY

from app.models import (
    AgendaItemRequest,
    AgentCardSearchRequest,
    AgentDispatchRequest,
    AgentTelemetryEventRequest,
    AttemptPayloadRequest,
    CreateUserRequest,
    ExamApprovalReviewRequest,
    ExamVisibilityRequest,
    ExamGenerationRequest,
    KnowledgeBase,
    PedagogicalReportRequest,
    PublishedExamUpdateRequest,
    PublishExamRequest,
    ProfileUpdateRequest,
    PublishRequest,
    StudentExamSubmitRequest,
    StudentGradingCallbackRequest,
)
from app.services.agentic_rag import call_agentic_workflow, call_pedagogical_report_workflow
from app.services.agentic_file_server import upload_to_agentic_file_server
from app.services.class_resources import (
    create_class_resource,
    delete_class_resource,
    get_class_resource_file,
    list_class_resources,
)
from app.services.student_workflow import (
    get_attempt_payload,
    list_student_attempts,
    prepare_agent_dispatch,
    save_student_grading_result,
    search_agent_card,
    retry_student_exam_workflow,
    submit_student_exam_attempt,
)
from app.services.supabase_admin import (
    create_agenda_as_staff,
    create_user_as_admin,
    delete_published_exam_as_staff,
    delete_profile_as_admin,
    get_current_user_from_token,
    get_agent_telemetry_dashboard,
    get_dashboard_metrics_for_staff,
    list_agenda_for_user,
    list_exam_results_for_staff,
    list_published_exams_for_user,
    list_profiles_as_admin,
    publish_exam_as_staff,
    review_exam_approval_as_admin,
    require_admin_access,
    save_pedagogical_report_if_present,
    save_agent_telemetry_event,
    set_exam_audit_run,
    update_published_exam_as_staff,
    update_published_exam_visibility_as_staff,
    update_profile_as_admin,
)
from app.services.storage import (
    clear_last_workflow_result,
    delete_knowledge_base,
    get_knowledge_base,
    load_last_workflow_result,
    load_knowledge_bases,
    save_last_workflow_result,
    save_uploaded_files,
)


app = FastAPI(title="Education Exam Agentic RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok"}


def _unwrap_agentic_json(value):
    current = value
    for _ in range(4):
        if isinstance(current, str):
            cleaned = current.replace("```json", "").replace("```", "").strip()
            try:
                current = json.loads(cleaned)
            except json.JSONDecodeError as error:
                raise HTTPException(status_code=422, detail="Telemetry payload is not valid JSON.") from error
            continue

        if not isinstance(current, dict):
            break

        wrapper = next(
            (
                key
                for key in ("text", "result", "payload", "input_value")
                if key in current and isinstance(current[key], (dict, str))
            ),
            None,
        )
        if wrapper is None:
            break
        current = current[wrapper]

    return current


@app.post("/api/telemetry/events", status_code=201)
async def create_telemetry_event(
    request: Request,
    x_telemetry_key: str = Header(default="", alias="X-Telemetry-Key"),
) -> dict:
    if TELEMETRY_API_KEY and not secrets.compare_digest(x_telemetry_key, TELEMETRY_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid telemetry API key.")

    payload = _unwrap_agentic_json(await request.json())
    try:
        validated = AgentTelemetryEventRequest.model_validate(payload)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors(include_url=False)) from error
    return save_agent_telemetry_event(validated)


@app.get("/api/telemetry/dashboard")
def get_telemetry_dashboard(
    period_days: int = 30,
    authorization: str = Header(default=""),
) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return get_agent_telemetry_dashboard(access_token, period_days)


@app.post("/api/workflow/callback")
async def receive_workflow_callback(request: Request) -> dict:
    payload = await request.json()
    result = save_last_workflow_result(payload)
    try:
        result["pedagogical_report_stored"] = save_pedagogical_report_if_present(payload)
    except HTTPException:
        result["pedagogical_report_stored"] = False
    return result


@app.get("/api/workflow/latest-result")
def get_latest_workflow_result() -> dict:
    payload = load_last_workflow_result()
    if payload is None:
        return {"status": "empty", "payload": None}
    return {"status": "success", "payload": payload}


@app.delete("/api/workflow/latest-result")
def delete_latest_workflow_result() -> dict:
    return clear_last_workflow_result()


@app.post("/api/file-server/test-upload")
def test_file_server_upload(file: UploadFile = File(...)) -> dict:
    content = file.file.read()
    try:
        file_path = upload_to_agentic_file_server(
            filename=file.filename or "document",
            content=content,
            content_type=file.content_type,
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "file_path": file_path,
    }


@app.get("/api/knowledge-bases")
def list_knowledge_bases() -> list[KnowledgeBase]:
    return load_knowledge_bases()


@app.post("/api/knowledge-bases")
def create_knowledge_base(
    name: str = Form(...),
    subject: str = Form(...),
    files: List[UploadFile] = File(...),
    authorization: str = Header(default=""),
) -> KnowledgeBase:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    if not files:
        raise HTTPException(status_code=400, detail="At least one document is required.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    current_user = get_current_user_from_token(access_token)

    kb = KnowledgeBase(name=name, subject=subject)
    try:
        saved_kb, _uploaded_documents = save_uploaded_files(kb, files, owner_id=current_user["id"])
    except Exception as error:
        try:
            delete_knowledge_base(kb.id)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"File server upload failed: {error}") from error
    return saved_kb


@app.post("/api/knowledge-bases/{kb_id}/index")
def index_existing_knowledge_base(kb_id: str):
    raise HTTPException(
        status_code=410,
        detail=(
            "Local re-indexing is disabled because files are no longer stored in backend/data. "
            "Upload the document again to index it from the real uploaded file."
        ),
    )


@app.post("/api/admin/users")
def create_user(
    request: CreateUserRequest,
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return create_user_as_admin(access_token, request)


@app.get("/api/admin/profiles")
def list_profiles(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return list_profiles_as_admin(access_token)


@app.patch("/api/admin/profiles/{profile_id}")
def update_profile(
    profile_id: str,
    request: ProfileUpdateRequest,
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return update_profile_as_admin(access_token, profile_id, request)


@app.delete("/api/admin/profiles/{profile_id}")
def delete_profile(profile_id: str, authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return delete_profile_as_admin(access_token, profile_id)


@app.post("/api/admin/pedagogical-reports")
def launch_pedagogical_report(
    request: PedagogicalReportRequest,
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    if request.analysis_type == "exam_audit" and not request.exam_id:
        raise HTTPException(status_code=422, detail="Select an exam for the audit.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    current_user = require_admin_access(access_token)
    try:
        return call_pedagogical_report_workflow(request, current_user["id"])
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/agenda")
def list_agenda(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return list_agenda_for_user(access_token)


@app.post("/api/agenda")
def create_agenda_item(
    request: AgendaItemRequest,
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return create_agenda_as_staff(access_token, request)


@app.get("/api/resources")
def list_resources(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    access_token = authorization.replace("Bearer ", "", 1).strip()
    return list_class_resources(access_token)


@app.post("/api/staff/resources")
def upload_resource(
    title: str = Form(...),
    description: str = Form(default=""),
    target_study_level: str = Form(...),
    file: UploadFile = File(...),
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    access_token = authorization.replace("Bearer ", "", 1).strip()
    return create_class_resource(
        access_token=access_token,
        title=title,
        description=description,
        target_study_level=target_study_level,
        filename=file.filename or "resource",
        content=file.file.read(),
    )


@app.get("/api/resources/{resource_id}/file")
def read_resource_file(resource_id: str, authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    access_token = authorization.replace("Bearer ", "", 1).strip()
    path, resource = get_class_resource_file(access_token, resource_id)
    return FileResponse(
        path=path,
        media_type=resource["content_type"],
        filename=resource["filename"],
        content_disposition_type="inline",
    )


@app.delete("/api/staff/resources/{resource_id}")
def remove_resource(resource_id: str, authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    access_token = authorization.replace("Bearer ", "", 1).strip()
    return delete_class_resource(access_token, resource_id)


@app.post("/api/exams/generate")
def generate_exam(request: ExamGenerationRequest):
    kb = get_knowledge_base(request.knowledge_base_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found.")

    try:
        if not kb.documents or not kb.documents[0].file_path:
            raise HTTPException(
                status_code=422,
                detail="No file_path found for this knowledge base. Upload the document with file server enabled.",
            )
        return call_agentic_workflow(
            request=request,
            kb=kb,
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/api/exams/published")
def list_published_exams(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return list_published_exams_for_user(access_token)


@app.get("/api/staff/results")
def list_staff_results(
    study_level: str = "",
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return list_exam_results_for_staff(access_token, study_level)


@app.get("/api/staff/dashboard")
def get_staff_dashboard(
    study_level: str = "Licence 2",
    academic_year: str = "2025-2026",
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return get_dashboard_metrics_for_staff(access_token, study_level, academic_year)


@app.post("/api/exams/publish")
def publish_generated_exam(
    request: PublishExamRequest,
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    exam = publish_exam_as_staff(access_token, request)
    current_user = get_current_user_from_token(access_token)
    now = datetime.now()
    academic_start = now.year if now.month >= 9 else now.year - 1
    report_request = PedagogicalReportRequest(
        analysis_type="exam_audit",
        study_level=exam.get("target_study_level") or request.target_study_level,
        academic_year=f"{academic_start}-{academic_start + 1}",
        exam_id=exam["id"],
    )
    try:
        run = call_pedagogical_report_workflow(
            report_request,
            current_user["id"],
            exam_context={
                "id": exam["id"],
                "title": exam.get("title") or "",
                "module": exam.get("module") or "",
                "target_study_level": exam.get("target_study_level") or request.target_study_level,
                "teacher_note": exam.get("teacher_note") or "",
                "exam": exam.get("exam") or {},
            },
        )
        exam = set_exam_audit_run(exam["id"], run=run)
        exam["approval_workflow"] = run
    except Exception as error:
        exam = set_exam_audit_run(exam["id"], error=str(error))
        exam["approval_workflow_error"] = str(error)
    return exam


@app.patch("/api/admin/exams/{exam_id}/approval")
def review_exam_approval(
    exam_id: str,
    request: ExamApprovalReviewRequest,
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return review_exam_approval_as_admin(access_token, exam_id, request)


@app.delete("/api/exams/published/{exam_id}")
def delete_published_exam(exam_id: str, authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return delete_published_exam_as_staff(access_token, exam_id)


@app.patch("/api/exams/published/{exam_id}")
def update_published_exam(
    exam_id: str,
    request: PublishedExamUpdateRequest,
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return update_published_exam_as_staff(access_token, exam_id, request)


@app.patch("/api/exams/published/{exam_id}/visibility")
def update_published_exam_visibility(
    exam_id: str,
    request: ExamVisibilityRequest,
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return update_published_exam_visibility_as_staff(access_token, exam_id, request)


@app.post("/api/student/attempts/submit")
def submit_student_attempt(
    request: StudentExamSubmitRequest,
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return submit_student_exam_attempt(access_token, request)


@app.get("/api/student/attempts")
def list_my_student_attempts(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return list_student_attempts(access_token)


@app.post("/api/student/attempts/{attempt_id}/retry-workflow")
def retry_my_student_workflow(
    attempt_id: str,
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return retry_student_exam_workflow(access_token, attempt_id)


@app.post("/api/a2a/actions/get-attempt-payload")
def a2a_get_attempt_payload(
    request: AttemptPayloadRequest,
):
    return get_attempt_payload(request.correlation_id)


@app.post("/api/a2a/actions/search-agent-card")
def a2a_search_agent_card(
    request: AgentCardSearchRequest,
):
    return search_agent_card(request)


@app.post("/api/a2a/actions/prepare-agent-dispatch")
def a2a_prepare_agent_dispatch(
    request: AgentDispatchRequest,
):
    return prepare_agent_dispatch(request)


@app.post("/api/student/grading/callback")
async def receive_student_grading_callback(request: Request):
    payload = await request.json()

    # Agentic components may wrap the useful JSON in text, result, or payload.
    for _ in range(3):
        if isinstance(payload, str):
            payload = json.loads(payload)
            continue

        wrapper = next(
            (key for key in ("text", "result", "payload") if isinstance(payload, dict) and key in payload),
            None,
        )
        if not wrapper:
            break
        payload = payload[wrapper]

    validated = StudentGradingCallbackRequest.model_validate(payload)
    return save_student_grading_result(validated)


@app.get("/api/exams/{exam_id}")
def get_exam(exam_id: str):
    raise HTTPException(status_code=501, detail="Exam persistence is not implemented yet.")


@app.post("/api/exams/{exam_id}/publish")
def publish_exam(exam_id: str, request: PublishRequest):
    raise HTTPException(status_code=501, detail="Exam publishing storage is not implemented yet.")
