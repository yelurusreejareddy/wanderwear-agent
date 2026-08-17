-- Real, urgent security fix: both wardrobe and inspiration buckets
-- were created public=true with an "allow all" policy, meaning
-- anyone with the app's own public anon key, which is meant to be
-- public, could list AND view every real photo, including real
-- mirror selfies. Flipping to private closes the fully-unauthenticated
-- public endpoint immediately. Removing the anon policy entirely means
-- no client-side key can read or list these files anymore at all,
-- only the real service role key can, and that key only ever lives in
-- a real backend's own .env, never in any file a browser can see.
update storage.buckets set public = false where id in ('wardrobe', 'inspiration');

drop policy if exists "temporary_allow_all_wardrobe_storage" on storage.objects;
drop policy if exists "temporary_allow_all_inspiration_storage" on storage.objects;

-- No new policy is created here on purpose. With no policy granting
-- anon (or any non-service-role caller) access, and RLS already on
-- by default, storage.objects is now real, actually private, the
-- service role key bypasses RLS entirely by design, which is exactly
-- the real, correct way for a trusted backend to still reach it.
