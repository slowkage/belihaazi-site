-- belihaazi.com: likes, comments and email subscribers.
-- Paste this whole file into Supabase → SQL Editor → Run. Safe to run again.
--
-- Readers never touch the tables directly. They can only call the functions at the bottom,
-- which check the input and limit how often one person can post.

-- ---------- tables ----------
create table if not exists like_votes (
  page       text not null,
  voter      uuid not null,               -- random id kept in the reader's browser
  ip_hash    text,
  created_at timestamptz not null default now(),
  primary key (page, voter)
);

create table if not exists comments (
  id         bigint generated always as identity primary key,
  page       text not null,
  name       text not null,
  body       text not null,
  created_at timestamptz not null default now(),
  visible    boolean not null default true, -- untick in the Table Editor to hide a comment
  ip_hash    text
);
create index if not exists comments_page on comments (page, created_at);

create table if not exists subscribers (
  email      text primary key,
  token      uuid not null default gen_random_uuid(),  -- used in the unsubscribe link
  active     boolean not null default true,
  created_at timestamptz not null default now(),
  ip_hash    text
);

create table if not exists announced (          -- posts already emailed to subscribers
  url        text primary key,
  title      text,
  at         timestamptz not null default now()
);

-- ---------- lock everything down ----------
alter table like_votes  enable row level security;
alter table comments    enable row level security;
alter table subscribers enable row level security;
alter table announced   enable row level security;
revoke all on like_votes, comments, subscribers, announced from anon, authenticated;

-- readers may read visible comments (but not the hashed IP)
drop policy if exists "read visible comments" on comments;
create policy "read visible comments" on comments for select to anon using (visible);
grant select (id, page, name, body, created_at) on comments to anon;

drop view if exists like_counts;   -- replaced by like_count() below

-- ---------- helpers ----------
create or replace function _ip_hash() returns text language sql stable set search_path = public as $$
  select md5(coalesce(
    current_setting('request.headers', true)::json->>'cf-connecting-ip',
    current_setting('request.headers', true)::json->>'x-real-ip',
    split_part(current_setting('request.headers', true)::json->>'x-forwarded-for', ',', 1),
    'none') || 'belihaazi')
$$;

create or replace function _valid_page(p text) returns boolean language sql immutable set search_path = public as $$
  select p ~ '^/(povs|prose|poems|reports|spoken-word|hip-hop)/[a-z0-9-]{1,80}/$'
$$;

-- ---------- what readers can call ----------
-- like (liked = true) or unlike (liked = false); returns the new count
create or replace function like_page(p text, vid uuid, liked boolean) returns int
language plpgsql security definer set search_path = public as $$
declare h text := _ip_hash();
begin
  if not _valid_page(p) then raise exception 'bad page'; end if;
  if liked then
    if (select count(*) from like_votes where ip_hash = h and created_at > now() - interval '1 hour') >= 60 then
      raise exception 'slow down';
    end if;
    insert into like_votes (page, voter, ip_hash) values (p, vid, h) on conflict do nothing;
  else
    delete from like_votes where page = p and voter = vid;
  end if;
  return (select count(*) from like_votes where page = p);
end $$;

-- add a comment; "website" is a hidden form field that only bots fill in
create or replace function add_comment(p text, author text, message text, website text default '')
returns table (id bigint, page text, name text, body text, created_at timestamptz)
language plpgsql security definer set search_path = public as $$
declare h text := _ip_hash(); n text := btrim(author); b text := btrim(message);
begin
  if coalesce(website, '') <> '' then return; end if;
  if not _valid_page(p) then raise exception 'bad page'; end if;
  if length(n) not between 1 and 60 then raise exception 'name must be 1 to 60 characters'; end if;
  if length(b) not between 2 and 2000 then raise exception 'comment must be 2 to 2000 characters'; end if;
  if (select count(*) from comments c where c.ip_hash = h and c.created_at > now() - interval '1 minute') >= 3
     or (select count(*) from comments c where c.ip_hash = h and c.created_at > now() - interval '1 day') >= 30
     or (select count(*) from comments c where c.created_at > now() - interval '1 minute') >= 20 then
    raise exception 'too many comments, try again in a minute';
  end if;
  return query insert into comments as c (page, name, body, ip_hash) values (p, n, b, h)
    returning c.id, c.page, c.name, c.body, c.created_at;
end $$;

-- subscribe to new-post emails
create or replace function subscribe(addr text, website text default '') returns boolean
language plpgsql security definer set search_path = public as $$
declare h text := _ip_hash(); e text := lower(btrim(addr));
begin
  if coalesce(website, '') <> '' then return true; end if;
  if length(e) > 254 or e !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then raise exception 'that email does not look right'; end if;
  if (select count(*) from subscribers s where s.ip_hash = h and s.created_at > now() - interval '1 hour') >= 5 then
    raise exception 'too many sign-ups, try later';
  end if;
  insert into subscribers as s (email, ip_hash) values (e, h)
    on conflict on constraint subscribers_pkey do update set active = true;
  return true;
end $$;

-- like count for a page, without exposing who liked
create or replace function like_count(p text) returns int
language sql stable security definer set search_path = public as $$
  select count(*)::int from like_votes where page = p
$$;

-- unsubscribe from the link in an email
create or replace function unsubscribe(t uuid) returns boolean
language plpgsql security definer set search_path = public as $$
begin
  update subscribers set active = false where token = t;
  return found;
end $$;

revoke all on function like_page(text, uuid, boolean), add_comment(text, text, text, text),
  subscribe(text, text), unsubscribe(uuid), _ip_hash(), _valid_page(text) from public;
grant execute on function like_page(text, uuid, boolean), add_comment(text, text, text, text),
  subscribe(text, text), unsubscribe(uuid) to anon;
revoke all on function _ip_hash(), _valid_page(text) from anon, authenticated;
revoke all on function like_count(text) from public, authenticated;
grant execute on function like_count(text) to anon;
revoke execute on function like_page(text, uuid, boolean), add_comment(text, text, text, text),
  subscribe(text, text), unsubscribe(uuid) from authenticated;
