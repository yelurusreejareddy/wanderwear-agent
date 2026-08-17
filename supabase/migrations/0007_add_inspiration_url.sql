-- Real request: a place to save the actual real purchase link for a
-- saved style, when one exists. Not every inspiration photo has one
-- (an Instagram post has no product page), so this stays nullable, a
-- real link when she has one, empty otherwise, never invented.
alter table style_inspiration add column product_url text;
