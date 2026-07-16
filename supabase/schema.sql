create type public.user_role as enum ('student', 'teacher', 'admin');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null default '',
  role public.user_role not null default 'student',
  study_level text,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users can read their own profile"
on public.profiles
for select
to authenticated
using (auth.uid() = id);

create policy "Users can update their own profile"
on public.profiles
for update
to authenticated
using (auth.uid() = id)
with check (auth.uid() = id);

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

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

create table public.agenda_items (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text not null default '',
  target_study_level text not null,
  evaluation_type text not null default 'Controle continu',
  scheduled_at timestamptz not null,
  created_by uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now()
);

alter table public.agenda_items enable row level security;

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
