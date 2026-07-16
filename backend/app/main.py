from typing import List

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    AgendaItemRequest,
    CreateUserRequest,
    ExamGenerationRequest,
    KnowledgeBase,
    PublishExamRequest,
    ProfileUpdateRequest,
    PublishRequest,
)
from app.services.agentic_rag import call_agentic_workflow
from app.services.agentic_file_server import upload_to_agentic_file_server
from app.services.supabase_admin import (
    create_agenda_as_staff,
    create_user_as_admin,
    delete_published_exam_as_staff,
    delete_profile_as_admin,
    get_current_user_from_token,
    list_agenda_for_user,
    list_published_exams_for_user,
    list_profiles_as_admin,
    publish_exam_as_staff,
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


@app.post("/api/workflow/callback")
async def receive_workflow_callback(request: Request) -> dict:
    payload = await request.json()
    return save_last_workflow_result(payload)


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


@app.post("/api/exams/publish")
def publish_generated_exam(
    request: PublishExamRequest,
    authorization: str = Header(default=""),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return publish_exam_as_staff(access_token, request)


@app.delete("/api/exams/published/{exam_id}")
def delete_published_exam(exam_id: str, authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    access_token = authorization.replace("Bearer ", "", 1).strip()
    return delete_published_exam_as_staff(access_token, exam_id)


@app.get("/api/exams/{exam_id}")
def get_exam(exam_id: str):
    raise HTTPException(status_code=501, detail="Exam persistence is not implemented yet.")


@app.post("/api/exams/{exam_id}/publish")
def publish_exam(exam_id: str, request: PublishRequest):
    raise HTTPException(status_code=501, detail="Exam publishing storage is not implemented yet.")
