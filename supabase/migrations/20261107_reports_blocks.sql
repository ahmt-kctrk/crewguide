-- ════════════════════════════════════════════════════════════════════════════
-- CrewGuide — Şikayet & engelleme + güvenlik düzeltmeleri (7 Kasım 2026)
--  • reports: yer / yorum / kullanıcı şikayeti (App Store 1.2)
--  • blocks: kullanıcı engelleme
--  • Aynı içeriği 3 farklı kişi şikayet ederse içerik otomatik gizlenir (admin inceler)
--  • comments.is_hidden: yorum gizleme (eskiden metin değiştiriliyordu)
--  • GÜVENLİK: kullanıcı kendi profilinde role='admin' yapamaz; is_disabled'ı açamaz
--  • GÜVENLİK: yorum başkası adına (user_id) eklenemez, gizli yorum sahibince açılamaz
-- Tekrar çalıştırmak güvenlidir.
-- ════════════════════════════════════════════════════════════════════════════

-- 0) Sistem işlemleri için bayrak: tetikleyicilerin "sadece admin" kontrolünü atlamasına izin verir
create or replace function public.cg_is_system()
returns boolean language sql stable as $$
  select coalesce(current_setting('cg.system', true), '') = 'on';
$$;

-- İstek bir uygulama kullanıcısından mı (PostgREST: anon/authenticated) yoksa sunucudan mı
-- (auth sunucusu, service_role, SQL Editor) geliyor? Sunucu işlemleri (ör. kullanıcı silinince
-- FK'nın user_id'yi NULL yapması) koruma tetikleyicilerine takılmamalı.
create or replace function public.cg_is_server()
returns boolean language sql stable as $$
  select coalesce(nullif(current_setting('role', true), ''), 'none') not in ('anon', 'authenticated');
$$;

-- 1) Profil koruması (role / is_disabled sadece admin veya sistem tarafından değişir)
create or replace function public.cg_profiles_protect()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if public.cg_is_server() or public.cg_is_system() or public.cg_is_admin() then
    return new;
  end if;
  if tg_op = 'INSERT' then
    new.role := 'user';
    new.is_disabled := false;
    new.disabled_at := null;
  else
    new.id := old.id;
    new.role := old.role;
    new.is_disabled := old.is_disabled;
    new.disabled_at := old.disabled_at;
  end if;
  return new;
end $$;

drop trigger if exists cg_profiles_protect on public.profiles;
create trigger cg_profiles_protect
  before insert or update on public.profiles
  for each row execute function public.cg_profiles_protect();

-- 2) Yorumlar: gizleme kolonu + sahiplik koruması
alter table public.comments add column if not exists is_hidden boolean not null default false;

create or replace function public.cg_comments_protect()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if public.cg_is_server() or public.cg_is_system() or public.cg_is_admin() then
    return new;
  end if;
  if tg_op = 'INSERT' then
    new.user_id := auth.uid();         -- başkası adına yorum yazılamaz
    new.is_hidden := false;
  else
    new.user_id := old.user_id;
    new.place_id := old.place_id;
    if old.is_hidden then new.is_hidden := true; end if;   -- gizlenen yorum sahibince açılamaz
  end if;
  return new;
end $$;

drop trigger if exists cg_comments_protect on public.comments;
create trigger cg_comments_protect
  before insert or update on public.comments
  for each row execute function public.cg_comments_protect();

drop policy if exists "Giris yapan okuyabilir" on public.comments;
drop policy if exists "cg read visible comments" on public.comments;
create policy "cg read visible comments" on public.comments
  for select to authenticated
  using (not is_hidden or user_id = auth.uid() or public.cg_is_admin());

-- 3) Yer güncelleme tetikleyicisi: sistem bayrağını ve sunucu işlemlerini tanısın
--    (DÜZELTME: eskiden yeri olan bir kullanıcı silinirken FK'nın user_id'yi NULL yapması bu
--     tetikleyiciye takılıp silmeyi engelliyordu)
create or replace function public.cg_places_before_update()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if public.cg_is_server() or public.cg_is_system() or public.cg_is_admin() then
    return new;
  end if;
  new.status  := old.status;
  new.user_id := old.user_id;
  if old.is_hidden and not new.is_hidden then
    new.is_hidden := true;
  end if;
  return new;
end $$;

-- 4) Şikayetler
create table if not exists public.reports (
  id             uuid primary key default gen_random_uuid(),
  reporter_id    uuid default auth.uid() references auth.users(id) on delete set null,
  target_type    text not null check (target_type in ('place', 'comment', 'user')),
  target_id      text not null,
  target_user_id uuid references auth.users(id) on delete set null,   -- içeriğin sahibi
  reason         text not null check (reason in ('spam', 'offensive', 'inaccurate', 'inappropriate', 'harassment', 'other')),
  details        text check (char_length(details) <= 500),
  status         text not null default 'open' check (status in ('open', 'resolved', 'dismissed')),
  created_at     timestamptz not null default now(),
  resolved_at    timestamptz,
  resolved_by    uuid references auth.users(id) on delete set null
);
create unique index if not exists reports_one_open_per_reporter
  on public.reports (reporter_id, target_type, target_id) where status = 'open';
create index if not exists reports_open_idx on public.reports (status, created_at desc);

alter table public.reports enable row level security;

drop policy if exists "cg insert own report" on public.reports;
create policy "cg insert own report" on public.reports
  for insert to authenticated
  with check (reporter_id = auth.uid() and status = 'open' and resolved_at is null and resolved_by is null);

drop policy if exists "cg read own or admin reports" on public.reports;
create policy "cg read own or admin reports" on public.reports
  for select to authenticated
  using (reporter_id = auth.uid() or public.cg_is_admin());

drop policy if exists "cg admin update reports" on public.reports;
create policy "cg admin update reports" on public.reports
  for update to authenticated using (public.cg_is_admin()) with check (public.cg_is_admin());

drop policy if exists "cg admin delete reports" on public.reports;
create policy "cg admin delete reports" on public.reports
  for delete to authenticated using (public.cg_is_admin());

-- 5) 3 farklı kişi şikayet edince otomatik gizle
create or replace function public.cg_reports_after_insert()
returns trigger language plpgsql security definer set search_path = public as $$
declare n int;
begin
  select count(distinct reporter_id) into n
    from public.reports
   where target_type = new.target_type and target_id = new.target_id and status = 'open';
  if n >= 3 then
    perform set_config('cg.system', 'on', true);
    if new.target_type = 'place' then
      update public.places set is_hidden = true, is_reported = true where id = new.target_id;
    elsif new.target_type = 'comment' then
      update public.comments set is_hidden = true where id::text = new.target_id;
    end if;
    perform set_config('cg.system', '', true);
  elsif new.target_type = 'place' then
    perform set_config('cg.system', 'on', true);
    update public.places set is_reported = true where id = new.target_id;
    perform set_config('cg.system', '', true);
  end if;
  return new;
end $$;

drop trigger if exists cg_reports_after_insert on public.reports;
create trigger cg_reports_after_insert
  after insert on public.reports
  for each row execute function public.cg_reports_after_insert();

-- 6) Engellemeler
create table if not exists public.blocks (
  blocker_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  blocked_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (blocker_id, blocked_id),
  check (blocker_id <> blocked_id)
);
alter table public.blocks enable row level security;

drop policy if exists "cg own blocks read" on public.blocks;
create policy "cg own blocks read" on public.blocks
  for select to authenticated using (blocker_id = auth.uid());
drop policy if exists "cg own blocks insert" on public.blocks;
create policy "cg own blocks insert" on public.blocks
  for insert to authenticated with check (blocker_id = auth.uid());
drop policy if exists "cg own blocks delete" on public.blocks;
create policy "cg own blocks delete" on public.blocks
  for delete to authenticated using (blocker_id = auth.uid());

-- 7) Kalıcı hesap silmede şikayet/engelleme kayıtları da temizlensin (FK'lar cascade / set null)
--    (blocks: cascade, reports: set null — ek işlem gerekmez)

-- 8) Kayıt: profilin kendi kodu (profiles.invite_code) çakışırsa kayıt düşmesin
--    (istemcinin ürettiği 3 karakterli kod zamanla çakışabilir → "Database error saving new user")
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  v_code  text := upper(trim(coalesce(new.raw_user_meta_data->>'invited_by', '')));
  v_pcode text := upper(trim(coalesce(new.raw_user_meta_data->>'invite_code', '')));
  i int;
begin
  if v_code <> '' and v_code <> 'CRW-MASTER' then
    update public.invite_codes
       set used_by = new.id, used_at = now()
     where code = v_code and used_by is null and used_at is null;
    if not found then
      raise exception 'INVITE_INVALID: davet kodu gecersiz veya kullanilmis';
    end if;
  end if;

  if v_pcode = '' or exists (select 1 from public.profiles where invite_code = v_pcode and id <> new.id) then
    loop
      v_pcode := 'CRW-' || upper(substr(md5(random()::text || clock_timestamp()::text), 1, 6));
      exit when not exists (select 1 from public.profiles where invite_code = v_pcode);
    end loop;
  end if;

  insert into public.profiles (id, username, invite_code, invited_by, created_at)
  values (
    new.id,
    coalesce(nullif(trim(new.raw_user_meta_data->>'username'), ''), 'user_' || substr(new.id::text, 1, 8)),
    v_pcode,
    nullif(v_code, ''),
    new.created_at
  )
  on conflict (id) do update set
    username    = excluded.username,
    invite_code = excluded.invite_code,
    invited_by  = excluded.invited_by;

  for i in 1..3 loop
    insert into public.invite_codes (code, created_by) values (public.cg_new_invite_code(), new.id);
  end loop;

  return new;
end $$;
