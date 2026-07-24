# EvalGuard AI

Plateforme de generation, validation, publication et correction d'examens
avec Vue.js, FastAPI, Supabase et des workflows Agentic RAG distants.

## Fonctions principales

- Authentification Supabase pour les roles `admin`, `teacher` et `student`.
- Import des supports de cours et creation des knowledge bases.
- Generation d'examens par webhook Agentic RAG.
- Validation par l'enseignant puis approbation par l'administration.
- Publication des examens pour une classe.
- Passage et correction des examens etudiants.
- Notes detaillees, agenda et ressources de classe.
- Analyse pedagogique et observabilite des agents.

## Architecture

```text
Frontend Vue.js (5173)
        |
        | HTTP + JWT Supabase
        v
Backend FastAPI (8020)
        |
        +--> Supabase Auth et PostgreSQL
        +--> File server Agentic
        +--> Webhooks AbaFusion
```

Les workflows sont executes sur AbaFusion. Le depot conserve seulement le
code frontend/backend qui prepare les donnees, appelle les webhooks et traite
leurs callbacks.

## Organisation

```text
backend/
  app/
    main.py                       Routes FastAPI
    models.py                     Schemas Pydantic
    config.py                     Lecture de backend/.env
    services/
      agentic_rag.py              Appels des workflows distants
      agentic_file_server.py      Upload vers le file server
      class_resources.py          Ressources PDF/images des classes
      rag_indexer.py              Indexation et embeddings
      storage.py                  Knowledge bases et callbacks
      student_workflow.py         Soumission et correction etudiante
      supabase_admin.py           Acces Supabase et operations metier

frontend/
  src/
    App.vue                       Navigation et etat principal
    components/                   Ecrans reutilisables
    services/api.js               Appels vers FastAPI
    services/supabase.js          Session et authentification
    styles.css                    Styles globaux

docs/
  agent_prompts.md                Prompts des agents
  fileserver_read_file_poc.md     Integration du file server
```

## Configuration frontend

Creer `frontend/.env` :

```env
VITE_API_BASE_URL=http://127.0.0.1:8020
VITE_SUPABASE_URL=https://PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_PUBLISHABLE_KEY
```

La cle frontend est une cle publique Supabase. Ne jamais placer la
`SUPABASE_SERVICE_ROLE_KEY` dans le frontend.

## Configuration backend

Creer `backend/.env` avec les variables utiles :

```env
SUPABASE_URL=https://PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_PUBLISHABLE_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY

AGENTIC_WEBHOOK_URL=https://stg-agentic.abafusion.ai/api/v1/webhook/...
PEDAGOGICAL_REPORT_WEBHOOK_URL=https://stg-agentic.abafusion.ai/api/v1/webhook/...

AGENTIC_FILE_SERVER_ENABLED=true
AGENTIC_FILE_UPLOAD_URL=https://...
AGENTIC_FILE_UPLOAD_TOKEN=...
AGENTIC_FILE_UPLOAD_FIELD=file

A2A_STUDENT_ORCHESTRATOR_WEBHOOK_URL=https://...
A2A_GRADING_AGENT_WEBHOOK_URL=https://...
A2A_DLQ_AGENT_WEBHOOK_URL=https://...

GOOGLE_API_KEY=...
GOOGLE_EMBEDDING_MODEL=models/gemini-embedding-001
GOOGLE_EMBEDDING_DIMENSIONS=768
```

Les fichiers `.env` sont locaux et ne doivent pas etre ajoutes a Git.

## Lancer le projet

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8020
```

- API : `http://127.0.0.1:8020`
- Swagger : `http://127.0.0.1:8020/docs`
- Sante : `http://127.0.0.1:8020/api/health`

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

- Interface : `http://127.0.0.1:5173`

## Flux des examens

1. L'enseignant importe un cours et demande un examen.
2. FastAPI transmet la demande et le chemin du fichier au workflow.
3. Le workflow genere et evalue l'examen.
4. Le callback renvoie le brouillon au backend.
5. L'enseignant soumet le brouillon a l'administration.
6. L'administration approuve ou refuse l'examen.
7. L'enseignant publie l'examen approuve pour les etudiants.
8. Les reponses etudiantes sont envoyees au workflow de correction.
9. Le callback de correction enregistre la note et les feedbacks.

## Donnees locales

Le dossier `backend/data` est recree automatiquement lorsque le backend doit
stocker un callback ou une ressource locale. Les donnees principales restent
dans Supabase.

## Verification

```powershell
cd frontend
npm run build
```

Le backend peut etre verifie avec :

```powershell
cd backend
python -c "from app.main import app; print(len(app.routes))"
```
