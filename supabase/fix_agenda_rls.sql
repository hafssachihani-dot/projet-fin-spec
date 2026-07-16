-- 1) Verify your users and roles.
-- Run this first, then check that your admin email has role = 'admin'.
select
  u.id,
  u.email,
  p.full_name,
  p.role,
  p.study_level
from auth.users u
left join public.profiles p on p.id = u.id
order by u.created_at desc;

-- 2) If your admin user has no profile row, create it.
-- Replace admin@example.com with your real admin email, then run only this block.
insert into public.profiles (id, full_name, role, study_level)
select id, coalesce(raw_user_meta_data ->> 'full_name', email), 'admin', null
from auth.users
where email = 'admin@example.com'
on conflict (id) do update
set role = 'admin',
    study_level = null;

-- 3) Make sure the agenda table can attach rows to the current logged-in user.
alter table public.agenda_items
alter column created_by set default auth.uid();

alter table public.agenda_items enable row level security;

-- 4) Recreate agenda policies.
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
  and exists (
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
  and exists (
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
