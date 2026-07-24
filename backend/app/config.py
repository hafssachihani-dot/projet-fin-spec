import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"


def load_env_file() -> None:
    if not ENV_FILE.exists():
        return

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        # In this POC, the local .env file is the source of truth.
        # This avoids keeping an old shell variable after changing the upload URL.
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


load_env_file()

AGENTIC_WEBHOOK_URL = os.getenv("AGENTIC_WEBHOOK_URL", "").strip()
PEDAGOGICAL_REPORT_WEBHOOK_URL = os.getenv("PEDAGOGICAL_REPORT_WEBHOOK_URL", "").strip()
AGENTIC_FILE_UPLOAD_URL = os.getenv("AGENTIC_FILE_UPLOAD_URL", "").strip()
AGENTIC_API_KEY = os.getenv("AGENTIC_API_KEY", "").strip()
AGENTIC_FILE_UPLOAD_TOKEN = os.getenv("AGENTIC_FILE_UPLOAD_TOKEN", "").strip()
AGENTIC_FILE_UPLOAD_FIELD = os.getenv("AGENTIC_FILE_UPLOAD_FIELD", "file").strip()
AGENTIC_FILE_SERVER_ENABLED = os.getenv("AGENTIC_FILE_SERVER_ENABLED", "false").strip().lower() == "true"
SUPABASE_URL = os.getenv("SUPABASE_URL", os.getenv("VITE_SUPABASE_URL", "")).strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", os.getenv("VITE_SUPABASE_ANON_KEY", "")).strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GOOGLE_EMBEDDING_MODEL = os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001").strip()
GOOGLE_EMBEDDING_DIMENSIONS = int(os.getenv("GOOGLE_EMBEDDING_DIMENSIONS", "768"))
A2A_STUDENT_ORCHESTRATOR_WEBHOOK_URL = os.getenv("A2A_STUDENT_ORCHESTRATOR_WEBHOOK_URL", "").strip()
A2A_GRADING_AGENT_WEBHOOK_URL = os.getenv("A2A_GRADING_AGENT_WEBHOOK_URL", "").strip()
A2A_DLQ_AGENT_WEBHOOK_URL = os.getenv("A2A_DLQ_AGENT_WEBHOOK_URL", "").strip()
TELEMETRY_API_KEY = os.getenv("TELEMETRY_API_KEY", "").strip()
