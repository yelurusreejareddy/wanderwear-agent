-- Real, live gap found wiring up the new /wardrobe and /inspiration
-- endpoints: the real service role key bypasses RLS by design, but
-- table-level GRANTs are a separate, earlier gate, the exact same
-- "two gates" lesson phase 5 taught with the anon key. service_role
-- never had an explicit SELECT grant on these two real tables.
grant select on public.wardrobe_items to service_role;
grant select on public.style_inspiration to service_role;
