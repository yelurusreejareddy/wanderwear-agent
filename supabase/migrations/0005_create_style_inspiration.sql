-- Phase 7.5: real saved style inspiration, screenshots and photos of
-- outfits Sreeja liked but does not own, separate from wardrobe_items
-- (what she actually owns) since these play a different real role: the
-- stylist recalls them and suggests what to buy, never treats them as
-- real items in her closet.
create table style_inspiration (
  id bigint generated always as identity primary key,
  file_name text not null,
  photo_url text not null,
  description text,
  source_brand text,
  source_product_name text,
  created_at timestamptz not null default now()
);

-- description: a real, honest description of the outfit/styling shown,
--   drafted by the vision model, never treated as fact about anything
--   she owns.
-- source_brand / source_product_name: only filled in when the real
--   photo is itself a shopping screenshot naming a real product, like
--   the Primark blouse screenshot, a direct, concrete buy suggestion
--   instead of a vague one, left null for anything else, an Instagram
--   post, a personal photo, no invented brand ever filled in here.

create policy "temporary_allow_all_access"
on style_inspiration
for all
using (true)
with check (true);

-- A second, separate Storage bucket, same reasoning as wardrobe's own
-- bucket in phase 7: a real, permanent public URL per photo, no auth
-- dance. Kept separate from the 'wardrobe' bucket so owned items and
-- inspiration photos never mix at the storage layer either.
insert into storage.buckets (id, name, public)
values ('inspiration', 'inspiration', true);

create policy "temporary_allow_all_inspiration_storage"
on storage.objects
for all
using (bucket_id = 'inspiration')
with check (bucket_id = 'inspiration');
