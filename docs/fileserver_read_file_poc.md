# POC Read File via file server

Objectif : tester une architecture ou la plateforme agentic fait elle-meme :

1. Read File
2. Split
3. Embedding
4. RAG
5. Generation / Evaluation de l'examen

## Flow

```text
Frontend
 -> upload PDF au backend

Backend
 -> upload PDF vers le file server de la plateforme agentic
 -> recoit un file_path compatible avec le noeud Read File
 -> stocke seulement metadata + file_path dans Supabase

Webhook
 -> recoit exam_request + file_path

Workflow
 -> Read File lit file_path
 -> Split Text
 -> Embeddings
 -> Vector DB / Retriever
 -> Agents
```

## Payload envoye au webhook

```json
{
  "input_value": "...",
  "input_type": "chat",
  "output_type": "chat",
  "file_path": "...",
  "server_file_path": "...",
  "exam_request": {
    "knowledge_base_id": "...",
    "module": "...",
    "duration": "...",
    "study_level": "...",
    "difficulty": "...",
    "evaluation_type": "...",
    "question_count": 20,
    "learning_objectives": "...",
    "constraints": "..."
  }
}
```

## Configuration du noeud Read File

Dans le noeud Read File :

- Si tu utilises `Server File Path`, mappe la valeur vers :

```text
file_path
```

ou :

```text
server_file_path
```

selon ce que la plateforme attend.

## Informations a demander

Il faut demander a la plateforme / a ton ami :

1. URL API pour uploader un fichier.
2. Type d'authentification : Bearer token, API key, autre.
3. Nom du champ multipart : `file`, `files`, autre.
4. Exemple de reponse JSON apres upload.
5. Le champ exact attendu par Read File : `file_path`, `path`, `id`, etc.

Sans ces informations, envoyer un simple chemin local depuis ton ordinateur ne suffit pas, car la plateforme distante ne peut pas lire `C:\Users\...`.
