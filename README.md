# Education Exam Agentic RAG

Projet simple en deux parties :

- `backend/` : API Python FastAPI pour uploader une knowledge base et lancer une generation d'examen.
- `frontend/` : interface Vue.js pour l'enseignant et aperçu étudiant.

Le moteur Agentic RAG est volontairement un mock lisible dans cette première version. Il est dans :

```txt
backend/app/services/agentic_rag.py
```

Plus tard, tu peux remplacer ce fichier par LangFlow, LangGraph, Chroma, Qdrant ou ton workflow réel.

## Architecture

```txt
Frontend Vue.js
  Upload PDF + formulaire examen
        |
        v
Backend FastAPI
  Sauvegarde knowledge base
  Génère examen mock Agentic RAG
  Retourne questions + rapport qualité
        |
        v
Vue.js
  Affiche validation enseignant
  Affiche aperçu étudiant
```

## Lancer le backend

```bash
cd education-exam-agentic-rag/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

API :

```txt
http://127.0.0.1:8010
```

Documentation FastAPI :

```txt
http://127.0.0.1:8010/docs
```

## Lancer le frontend

```bash
cd education-exam-agentic-rag/frontend
npm install
npm run dev
```

Interface :

```txt
http://127.0.0.1:5173
```

## Supabase Auth

Le frontend utilise Supabase pour l'authentification avec 3 roles :

- `student`
- `teacher`
- `admin`

Dans Supabase, execute le SQL :

```txt
supabase/schema.sql
```

Puis cree le fichier :

```txt
frontend/.env
```

avec :

```txt
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_BASE_URL=http://127.0.0.1:8010
```

Pour permettre a l'administration de creer des etudiants, ajoute aussi dans :

```txt
backend/.env
```

les variables serveur :

```txt
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-publishable-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

La `SUPABASE_SERVICE_ROLE_KEY` se trouve dans Supabase :

```txt
Project Settings -> API -> service_role key
```

Ne mets jamais cette cle dans `frontend/.env`.

## Flux utilisateur

1. L'enseignant crée une knowledge base.
2. Il upload un PDF, DOCX, TXT ou MD.
3. Il remplit les paramètres de l'examen.
4. Le backend appelle le webhook Agentic RAG reel.
5. Le frontend affiche la reponse reelle du workflow.

## Webhook Agentic RAG

Le webhook est configure dans :

```txt
backend/.env
```

Exemple :

```txt
AGENTIC_WEBHOOK_URL=https://stg-agentic.abafusion.ai/api/v1/webhook/your-webhook-id
```

Le backend envoie au workflow :

- `input_value` avec les parametres de l'examen ;
- les informations de la knowledge base ;
- les chemins serveur des documents uploades.

Important : si le workflow distant doit lire un PDF avec un node `Read File`, le fichier doit etre accessible par ce workflow distant. Un chemin Windows local ne peut pas etre lu directement par un serveur distant.
