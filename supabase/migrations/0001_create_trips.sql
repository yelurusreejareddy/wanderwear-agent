-- Phase 5: the agent's first real memory table. One row per real
-- question and answer, so a future run can look back at what happened
-- before instead of starting from zero.
create table trips (
  id bigint generated always as identity primary key,
  question text not null,
  answer text not null,
  created_at timestamptz not null default now()
);

-- RLS is on by default for every new table (see phase 0 in the docs), so
-- without a policy, nobody, not even our own code, can read or write here.
-- This one is intentionally permissive and temporary, there is no login
-- system yet to check a real identity against. Phase 12 replaces this with
-- a real per-user policy once Supabase Auth exists.
create policy "temporary_allow_all_access"
on trips
for all
using (true)
with check (true);
