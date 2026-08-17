-- Phase 5, follow-up: creating the table and an RLS policy was not enough.
-- We deliberately unchecked "Automatically expose new tables" back in
-- phase 0, so new tables start with no table-level API access at all, a
-- separate, earlier gate than RLS. This grants our anon key just the two
-- permissions our code actually uses, read and write, nothing more.
grant select, insert on public.trips to anon;
