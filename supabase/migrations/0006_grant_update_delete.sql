-- Real, live need: fixing a bad draft label (wardrobe_items or
-- style_inspiration) needs update/delete, which we never granted, only
-- select/insert. Also needed for Sreeja's own future review/correction
-- pass, not just this one fix, so grant it on both real tables now.
grant update, delete on public.wardrobe_items to anon;
grant update, delete on public.style_inspiration to anon;
