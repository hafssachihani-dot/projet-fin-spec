from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ExamStatus(str, Enum):
    draft = "draft"
    pending_validation = "pending_validation"
    published = "published"


class KnowledgeBaseDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str
    file_path: str
    content_type: str
    size_bytes: int


class KnowledgeBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    subject: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    documents: List[KnowledgeBaseDocument] = Field(default_factory=list)


class ExamGenerationRequest(BaseModel):
    knowledge_base_id: str
    module: str
    duration: str
    study_level: str
    difficulty: str
    evaluation_type: str
    question_type: str = "QCM"
    question_count: int = Field(ge=1, le=100)
    learning_objectives: str
    constraints: Optional[str] = ""


class ExamQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    prompt: str
    expected_answer: str
    points: float
    quality_notes: List[str] = Field(default_factory=list)


class QualityReport(BaseModel):
    alignment_score: int
    clarity_score: int
    difficulty_score: int
    equity_score: int
    global_score: int
    detected_issues: List[str]
    applied_corrections: List[str]
    pedagogical_justification: str


class AgentStep(BaseModel):
    name: str
    status: str
    detail: str


class GeneratedExam(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: ExamStatus = ExamStatus.pending_validation
    created_at: datetime = Field(default_factory=datetime.utcnow)
    request: ExamGenerationRequest
    questions: List[ExamQuestion]
    report: QualityReport
    agent_steps: List[AgentStep]
    teacher_note: Optional[str] = None


class PublishRequest(BaseModel):
    teacher_note: Optional[str] = ""


class PublishExamRequest(BaseModel):
    exam: dict
    target_study_level: str
    teacher_note: Optional[str] = ""


class ExamVisibilityRequest(BaseModel):
    status: Literal["published", "hidden"]


class CreateUserRequest(BaseModel):
    full_name: str
    email: str
    password: str = Field(min_length=6)
    role: Literal["student", "teacher"]
    study_level: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    full_name: str
    role: Literal["student", "teacher", "admin"]
    study_level: Optional[str] = None


class AgendaItemRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    target_study_level: str
    evaluation_type: str
    scheduled_at: str
