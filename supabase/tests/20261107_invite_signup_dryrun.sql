-- ════════════════════════════════════════════════════════════════════════════
-- DENEME (DRY RUN) — 20261107_invite_signup_fix.sql
-- Migration'ı test kullanıcılarıyla çalıştırır, sonuçları HATA MESAJI olarak gösterir ve
-- HER ŞEYİ GERİ ALIR (veritabanında hiçbir şey kalıcı değişmez).
-- Beklenen: "DRYRUN RESULTS (rolled back)" ile başlayan bir hata ve altında sonuç listesi.
-- ════════════════════════════════════════════════════════════════════════════
do $outer$
declare res text;
begin
execute $mig$-- ════════════════════════════════════════════════════════════════════════════
-- CrewGuide — Davet kodlu kayıt düzeltmesi (7 Kasım 2026)
--  • Davet kodu kontrolü ve "kullanıldı" işaretleme artık SUNUCUDA (kayıt trigger'ı).
--    E-posta doğrulamalı kayıtta da çalışır (eskiden yalnızca istemcideydi).
--  • Yeni kullanıcının 3 davet kodu sunucuda üretilir (doğrulamalı kayıtta hiç üretilmiyordu).
--  • invite_codes herkese açık okuma/yazma politikaları kapatıldı (kod listesi toplanamaz,
--    herkes kod üretemez/değiştiremez). Kod kontrolü check_invite_code() ile.
--  • Kullanıcı silinince bağlı satırlar engel olmasın (FK → ON DELETE SET NULL).
--  • Kodu olmayan mevcut kullanıcılara 3'er kod verilir.
-- Tekrar çalıştırmak güvenlidir.
-- ════════════════════════════════════════════════════════════════════════════

-- 1) Rastgele davet kodu üretici (CRW-XXXXX, çakışmasız)
create or replace function public.cg_new_invite_code()
returns text language plpgsql volatile set search_path = public as $$
declare c text;
begin
  loop
    c := 'CRW-' || upper(substr(md5(random()::text || clock_timestamp()::text), 1, 5));
    exit when not exists (select 1 from public.invite_codes where code = c);
  end loop;
  return c;
end $$;

-- 2) Davet kodu geçerli mi? (giriş yapmamış kullanıcı da çağırabilir; sadece true/false döner)
create or replace function public.check_invite_code(p_code text)
returns boolean language sql stable security definer set search_path = public as $$
  select upper(trim(coalesce(p_code, ''))) = 'CRW-MASTER'
      or exists (select 1 from public.invite_codes
                 where code = upper(trim(p_code)) and used_by is null and used_at is null);
$$;
revoke all on function public.check_invite_code(text) from public;
grant execute on function public.check_invite_code(text) to anon, authenticated;

-- 3) Kayıt trigger'ı: kodu doğrula + kullanıldı işaretle + profil + 3 yeni kod
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  v_code text := upper(trim(coalesce(new.raw_user_meta_data->>'invited_by', '')));
  i int;
begin
  if v_code <> '' and v_code <> 'CRW-MASTER' then
    update public.invite_codes
       set used_by = new.id, used_at = now()
     where code = v_code and used_by is null and used_at is null;
    if not found then
      -- Kayıt iptal edilir; istemci bu mesajı "geçersiz/kullanılmış kod" olarak gösterir
      raise exception 'INVITE_INVALID: davet kodu gecersiz veya kullanilmis';
    end if;
  end if;

  insert into public.profiles (id, username, invite_code, invited_by, created_at)
  values (
    new.id,
    coalesce(nullif(trim(new.raw_user_meta_data->>'username'), ''), 'user_' || substr(new.id::text, 1, 8)),
    coalesce(new.raw_user_meta_data->>'invite_code', 'CRW-' || upper(substr(new.id::text, 1, 6))),
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

-- 4) Politikalar: herkese açık okuma/yazma kapatılır
drop policy if exists "Herkes davet kodu kontrol edebilir" on public.invite_codes;
drop policy if exists "Sistem davet kodu ekleyebilir" on public.invite_codes;
drop policy if exists "Sistem davet kodunu guncelleyebilir" on public.invite_codes;
drop policy if exists "Admin invite_codes görebilir" on public.invite_codes;
drop policy if exists "Admin invite_codes ekleyebilir" on public.invite_codes;
drop policy if exists "Auth users can read invite codes" on public.invite_codes;
drop policy if exists "Auth users can insert invite codes" on public.invite_codes;
drop policy if exists "Owner or admin can update invite code" on public.invite_codes;

alter table public.invite_codes enable row level security;

drop policy if exists "cg own or admin read invite codes" on public.invite_codes;
create policy "cg own or admin read invite codes" on public.invite_codes
  for select to authenticated
  using (created_by = auth.uid() or public.cg_is_admin());

drop policy if exists "cg admin insert invite codes" on public.invite_codes;
create policy "cg admin insert invite codes" on public.invite_codes
  for insert to authenticated with check (public.cg_is_admin());

drop policy if exists "cg admin update invite codes" on public.invite_codes;
create policy "cg admin update invite codes" on public.invite_codes
  for update to authenticated using (public.cg_is_admin()) with check (public.cg_is_admin());

drop policy if exists "cg admin delete invite codes" on public.invite_codes;
create policy "cg admin delete invite codes" on public.invite_codes
  for delete to authenticated using (public.cg_is_admin());

-- 5) Kullanıcı silinince bağlı satırlar silmeyi engellemesin
alter table public.invite_codes drop constraint if exists invite_codes_used_by_fkey;
alter table public.invite_codes add constraint invite_codes_used_by_fkey
  foreign key (used_by) references auth.users(id) on delete set null;
alter table public.invite_codes drop constraint if exists invite_codes_created_by_fkey;
alter table public.invite_codes add constraint invite_codes_created_by_fkey
  foreign key (created_by) references auth.users(id) on delete set null;
alter table public.comments drop constraint if exists comments_user_id_fkey;
alter table public.comments add constraint comments_user_id_fkey
  foreign key (user_id) references auth.users(id) on delete set null;
alter table public.places drop constraint if exists places_user_id_fkey;
alter table public.places add constraint places_user_id_fkey
  foreign key (user_id) references auth.users(id) on delete set null;
alter table public.ratings drop constraint if exists ratings_user_id_fkey;
alter table public.ratings add constraint ratings_user_id_fkey
  foreign key (user_id) references auth.users(id) on delete set null;

-- 6) Davet kodu olmayan mevcut kullanıcılara 3'er kod
do $$
declare u record; i int;
begin
  for u in select id from auth.users au
           where not exists (select 1 from public.invite_codes c where c.created_by = au.id) loop
    for i in 1..3 loop
      insert into public.invite_codes (code, created_by) values (public.cg_new_invite_code(), u.id);
    end loop;
  end loop;
end $$;
$mig$;
execute $t$
create temp table _r(step text, ok text) ;
insert into public.invite_codes(code, created_by) values ('CRW-TEST1', null);
-- 1) geçerli kodla kayıt
insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values ('00000000-0000-0000-0000-000000000000', '11111111-1111-1111-1111-111111111111', 'authenticated','authenticated','t1@example.invalid',
        '{"username":"tester1","invited_by":"crw-test1","invite_code":"CRW-ABC"}', now(), now());
insert into _r select 'code marked used', (select (used_by='11111111-1111-1111-1111-111111111111')::text from public.invite_codes where code='CRW-TEST1');
insert into _r select 'profile', (select username||' / '||coalesce(invited_by,'-') from public.profiles where id='11111111-1111-1111-1111-111111111111');
insert into _r select 'new codes', (select count(*)::text from public.invite_codes where created_by='11111111-1111-1111-1111-111111111111');
insert into _r select 'check used code', public.check_invite_code('CRW-TEST1')::text;
insert into _r select 'check master', public.check_invite_code('crw-master')::text;
-- 2) kullanılmış kodla ikinci kayıt → hata bekleniyor
do $x$ begin
  insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at)
  values ('00000000-0000-0000-0000-000000000000', '22222222-2222-2222-2222-222222222222', 'authenticated','authenticated','t2@example.invalid',
          '{"username":"tester2","invited_by":"CRW-TEST1"}', now(), now());
  insert into _r values ('reuse rejected','NO (BUG)');
exception when others then insert into _r values ('reuse rejected', 'yes: '||left(sqlerrm,60)); end $x$;
-- 3) master
insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values ('00000000-0000-0000-0000-000000000000', '33333333-3333-3333-3333-333333333333', 'authenticated','authenticated','t3@example.invalid',
        '{"username":"tester3","invited_by":"CRW-MASTER"}', now(), now());
insert into _r select 'master signup codes', (select count(*)::text from public.invite_codes where created_by='33333333-3333-3333-3333-333333333333');
-- 4) silme engellenmiyor
delete from auth.users where id='11111111-1111-1111-1111-111111111111';
insert into _r select 'delete ok, code still used', (select (used_by is null and used_at is not null)::text from public.invite_codes where code='CRW-TEST1');
insert into _r select 'check after delete', public.check_invite_code('CRW-TEST1')::text;
insert into _r select 'users without codes after backfill', (select count(*)::text from auth.users au where not exists (select 1 from public.invite_codes c where c.created_by=au.id));
insert into _r select 'policies', (select string_agg(polname, ' | ') from pg_policy where polrelid='public.invite_codes'::regclass);

$t$;
select string_agg(step||' = '||ok, E'\n') into res from _r;
raise exception 'DRYRUN RESULTS (rolled back):%', E'\n'||res;
end $outer$;