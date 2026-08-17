-- Phase 7, follow-up: same real gap phase 5 hit with trips. Creating the
-- table and an RLS policy is not enough, table-level API access is a
-- separate, earlier gate. This grants our anon key read and write on the
-- new table, nothing more.
grant select, insert on public.wardrobe_items to anon;
