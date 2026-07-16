create extension if not exists vector;

create table if not exists public.retrieval_sessions (
  id uuid primary key default gen_random_uuid(),
  knowledge_base_id text not null,
  purpose text not null default 'exam_generation',
  retrieval_query text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.retrieval_context_chunks (
  id uuid primary key default gen_random_uuid(),
  retrieval_session_id uuid not null references public.retrieval_sessions(id) on delete cascade,
  knowledge_base_id text not null,
  document_id text not null,
  filename text not null,
  content text not null,
  page_number int,
  chunk_index int not null,
  similarity_score float not null default 0,
  embedding vector(768),
  created_at timestamptz not null default now()
);

create index if not exists retrieval_sessions_kb_created_idx
on public.retrieval_sessions (knowledge_base_id, created_at desc);

create index if not exists retrieval_context_session_score_idx
on public.retrieval_context_chunks (retrieval_session_id, similarity_score desc);

create index if not exists retrieval_context_embedding_idx
on public.retrieval_context_chunks
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

alter table public.retrieval_sessions enable row level security;
alter table public.retrieval_context_chunks enable row level security;

-- Backend access uses SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS.
-- If your workflow SQL node connects directly to Postgres, it can read these
-- tables with the database credentials you configure in that node.
