alter table public.profiles
add column if not exists study_level text;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, full_name, role, study_level)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', ''),
    coalesce(new.raw_user_meta_data ->> 'role', 'student')::public.user_role,
    new.raw_user_meta_data ->> 'study_level'
  );
  return new;
end;
$$;

create table if not exists public.agenda_items (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text not null default '',
  target_study_level text not null,
  evaluation_type text not null default 'Controle continu',
  scheduled_at timestamptz not null,
  created_by uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now()
);

alter table public.agenda_items
alter column created_by set default auth.uid();

alter table public.agenda_items enable row level security;

drop policy if exists "Users can read agenda for their role" on public.agenda_items;
create policy "Users can read agenda for their role"
on public.agenda_items
for select
to authenticated
using (
  exists (
    select 1
    from public.profiles p
    where p.id = auth.uid()
      and (
        p.role in ('teacher', 'admin')
        or (p.role = 'student' and p.study_level = agenda_items.target_study_level)
      )
  )
);

drop policy if exists "Teachers and admins can create agenda items" on public.agenda_items;
create policy "Teachers and admins can create agenda items"
on public.agenda_items
for insert
to authenticated
with check (
  created_by = auth.uid()
  and
  exists (
    select 1
    from public.profiles p
    where p.id = auth.uid()
      and p.role in ('teacher', 'admin')
  )
);

drop policy if exists "Teachers and admins can update agenda items" on public.agenda_items;
create policy "Teachers and admins can update agenda items"
on public.agenda_items
for update
to authenticated
using (
  exists (
    select 1
    from public.profiles p
    where p.id = auth.uid()
      and p.role in ('teacher', 'admin')
  )
)
with check (
  created_by = auth.uid()
  and
  exists (
    select 1
    from public.profiles p
    where p.id = auth.uid()
      and p.role in ('teacher', 'admin')
  )
);

drop policy if exists "Teachers and admins can delete agenda items" on public.agenda_items;
create policy "Teachers and admins can delete agenda items"
on public.agenda_items
for delete
to authenticated
using (
  exists (
    select 1
    from public.profiles p
    where p.id = auth.uid()
      and p.role in ('teacher', 'admin')
  )
);
