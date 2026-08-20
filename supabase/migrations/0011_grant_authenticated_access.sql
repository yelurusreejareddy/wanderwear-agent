-- Real, live bug found testing phase 12 end to end: "permission denied
-- for table wardrobe_items", even with a real, valid, logged-in
-- token. Same real "two gates" lesson as phase 5 (anon) and phase 10
-- (service_role): RLS and table-level GRANTs are separate, both must
-- allow it. A real, authenticated PostgREST request runs as the
-- "authenticated" role, not "anon", and it never had its own grant,
-- only anon did, back when there was no real login to tell them apart.
grant select, insert, update, delete on public.trips to authenticated;
grant select, insert, update, delete on public.wardrobe_items to authenticated;
grant select, insert, update, delete on public.style_inspiration to authenticated;
