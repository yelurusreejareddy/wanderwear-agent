-- Phase 12: real per-user data, replacing the temporary_allow_all
-- policies every table has had since phase 5/7/7.5. Real login now
-- exists (Supabase Auth's own auth.users table, a real account
-- already created there), so this is the first point every table can
-- actually check "who is this" instead of trusting anyone with the key.

-- Step 1: add a real user_id column to every real table, pointing at
-- the real, permanent id Supabase Auth assigns each account. Starts
-- nullable, existing real rows have no real owner yet, filled in next.
alter table trips add column user_id uuid references auth.users(id);
alter table wardrobe_items add column user_id uuid references auth.users(id);
alter table style_inspiration add column user_id uuid references auth.users(id);

-- Step 2: backfill. Every real row created before real login existed
-- was genuinely Sreeja's own data, her real new account id is the
-- correct, honest owner for all of it, not a guess.
update trips set user_id = 'fb26c600-bd56-4588-bf0e-563311d78f30' where user_id is null;
update wardrobe_items set user_id = 'fb26c600-bd56-4588-bf0e-563311d78f30' where user_id is null;
update style_inspiration set user_id = 'fb26c600-bd56-4588-bf0e-563311d78f30' where user_id is null;

-- Step 3: now that every real row has a real owner, require it going
-- forward too. No default value on purpose, once a second real user
-- exists, a silent default would keep quietly assigning their new
-- data to Sreeja's account, a real, dangerous mistake. Every future
-- insert must explicitly say which real, logged-in user it belongs to.
alter table trips alter column user_id set not null;
alter table wardrobe_items alter column user_id set not null;
alter table style_inspiration alter column user_id set not null;

-- Step 4: replace the temporary, permissive policies with real
-- per-user ones. auth.uid() is a real Supabase function, it reads the
-- real logged-in user's id straight out of the request's own verified
-- token, not anything the client could fake by just sending a
-- different value. USING controls what a real user can SEE (select/
-- update/delete targets), WITH CHECK controls what they're allowed to
-- WRITE (insert/update), both need the same real rule here, you may
-- only ever touch your own real rows.
drop policy if exists "temporary_allow_all_access" on trips;
create policy "users_manage_own_trips"
on trips
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "temporary_allow_all_access" on wardrobe_items;
create policy "users_manage_own_wardrobe_items"
on wardrobe_items
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "temporary_allow_all_access" on style_inspiration;
create policy "users_manage_own_style_inspiration"
on style_inspiration
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
