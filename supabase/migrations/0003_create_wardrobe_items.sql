-- Phase 7: real wardrobe items, one row per real photographed piece of
-- clothing. Same shape decision as trips: a plain table, RLS on by
-- default, a temporary permissive policy until phase 12 adds real login.
create table wardrobe_items (
  id bigint generated always as identity primary key,
  file_name text not null,
  photo_url text not null,
  category text,
  color text,
  style_notes text,
  occasion_tags text,
  created_at timestamptz not null default now()
);

-- category: a plain word like "top", "dress", "pants", "jacket".
-- color: the real color, in plain words, this is exactly what tells two
--   black leather jackets apart from each other in a text answer.
-- style_notes: a short real description, "cropped, ribbed, off-shoulder".
-- occasion_tags: comma separated, "casual, date night, formal", etc.
-- category/color/style_notes start as a DRAFT from the vision model, not
-- fact, real confirmation/correction happens before we trust this data
-- for real outfit suggestions.

create policy "temporary_allow_all_access"
on wardrobe_items
for all
using (true)
with check (true);

-- Real photo files need somewhere to live. A Supabase Storage bucket is
-- just a row in storage.buckets, made with plain SQL, same as any other
-- table, no dashboard clicking required. public = true means each photo
-- gets a real, permanent, readable URL, so later the agent (or a real
-- frontend in phase 13) can just hand that URL back, no auth dance needed
-- to view your own wardrobe photos.
insert into storage.buckets (id, name, public)
values ('wardrobe', 'wardrobe', true);

-- storage.objects has its own RLS, separate from the wardrobe_items
-- table's RLS above, same two-gate pattern phase 5 already taught us.
-- Same temporary, permissive choice, real auth comes in phase 12.
create policy "temporary_allow_all_wardrobe_storage"
on storage.objects
for all
using (bucket_id = 'wardrobe')
with check (bucket_id = 'wardrobe');
