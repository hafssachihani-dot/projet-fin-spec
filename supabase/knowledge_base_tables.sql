create table if not exists public.knowledge_bases (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references public.profiles(id) on delete set null,
  name text not null,
  subject text not null,
  created_at timestamptz not null default now()
);

alter table public.knowledge_bases
add column if not exists owner_id uuid references public.profiles(id) on delete set null;

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  knowledge_base_id uuid not null references public.knowledge_bases(id) on delete cascade,
  filename text not null,
  file_path text not null default '',
  content_type text not null default 'application/octet-stream',
  size_bytes bigint not null default 0,
  created_at timestamptz not null default now()
);

alter table public.documents
add column if not exists file_path text not null default '';

alter table public.documents
add column if not exists content_type text not null default 'application/octet-stream';

alter table public.documents
add column if not exists size_bytes bigint not null default 0;

create index if not exists documents_knowledge_base_id_idx
on public.documents (knowledge_base_id);
