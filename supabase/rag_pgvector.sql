create extension if not exists vector;

create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  knowledge_base_id text not null,
  document_id text not null,
  filename text not null,
  content text not null,
  page_number int,
  chunk_index int not null,
  embedding vector(768),
  created_at timestamptz not null default now()
);

create index if not exists document_chunks_embedding_idx
on public.document_chunks
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

create or replace function public.match_document_chunks(
  query_embedding vector(768),
  match_knowledge_base_id text,
  match_count int default 8
)
returns table (
  id uuid,
  knowledge_base_id text,
  document_id text,
  filename text,
  content text,
  page_number int,
  chunk_index int,
  similarity float
)
language sql stable
as $$
  select
    dc.id,
    dc.knowledge_base_id,
    dc.document_id,
    dc.filename,
    dc.content,
    dc.page_number,
    dc.chunk_index,
    1 - (dc.embedding <=> query_embedding) as similarity
  from public.document_chunks dc
  where dc.knowledge_base_id = match_knowledge_base_id
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;
