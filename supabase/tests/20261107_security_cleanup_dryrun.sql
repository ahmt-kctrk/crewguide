-- KURU ÇALIŞTIRMA: hiçbir şey kaydedilmez, sonunda sonuçları hata mesajı olarak gösterir.
do $outer$
declare res text;
begin
execute $mig$-- ════════════════════════════════════════════════════════════════════════════
-- CrewGuide — Küçük güvenlik temizliği (7 Kasım 2026)
--  • Tetikleyici fonksiyonları dışarıdan (/rest/v1/rpc/...) çağrılamaz hale getirilir.
--    (Tetikleyiciler çalışmaya devam eder — PostgreSQL tetikleyici çalışırken bu yetkiye bakmaz.)
--  • cg_is_admin / cg_is_trusted: giriş yapmamış (anon) kullanıcı çağıramaz; giriş yapmış
--    kullanıcı çağırabilir (veritabanı kuralları bunları kullanıcı adına çalıştırır — gerekli).
--  • cg_is_system / cg_is_server: search_path sabitlenir.
--  • cg_new_invite_code: sadece sunucu kullanır; yeni kodlar 6 karakter, karışmayan harf/rakam,
--    kriptografik rastgele (CRW-XXXXXX, ~1 milyar ihtimal). Eskiden 5 hex (~1 milyon) —
--    deneme-yanılmayla bulunabilirdi. Mevcut kodlar geçerli kalır.
--  • CRW-MASTER ana kodu KALDIRILDI (uygulama kaynağında görünüyordu → herkes davetsiz kayıt olabiliyordu).
--  • Davet kodu olmadan kayıt artık sunucuda da reddedilir (eskiden boş kodla API'den kayıt olunabiliyordu).
-- Tekrar çalıştırmak güvenlidir.
-- ════════════════════════════════════════════════════════════════════════════

-- 1) Tetikleyici fonksiyonları: kimse doğrudan çağıramaz
revoke execute on function public.cg_comments_protect()      from public, anon, authenticated;
revoke execute on function public.cg_places_before_insert()  from public, anon, authenticated;
revoke execute on function public.cg_places_before_update()  from public, anon, authenticated;
revoke execute on function public.cg_profiles_protect()      from public, anon, authenticated;
revoke execute on function public.cg_reports_after_insert()  from public, anon, authenticated;
revoke execute on function public.handle_new_user()          from public, anon, authenticated;

-- 2) Rol kontrolleri: sadece giriş yapmış kullanıcılar (kurallar için gerekli)
revoke execute on function public.cg_is_admin()   from public, anon;
revoke execute on function public.cg_is_trusted() from public, anon;
grant  execute on function public.cg_is_admin()   to authenticated;
grant  execute on function public.cg_is_trusted() to authenticated;

-- 3) search_path sabitle
create or replace function public.cg_is_system()
returns boolean language sql stable set search_path = '' as $$
  select coalesce(current_setting('cg.system', true), '') = 'on';
$$;

create or replace function public.cg_is_server()
returns boolean language sql stable set search_path = '' as $$
  select coalesce(nullif(current_setting('role', true), ''), 'none') not in ('anon', 'authenticated');
$$;

-- 4) Daha güçlü davet kodu üretici (sadece sunucu kullanır)
create or replace function public.cg_new_invite_code()
returns text language plpgsql volatile set search_path = public as $$
declare
  alphabet constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';  -- 32 karakter, 0/O/1/I yok
  b bytea;
  c text;
  i int;
begin
  loop
    b := extensions.gen_random_bytes(6);
    c := 'CRW-';
    for i in 0..5 loop
      c := c || substr(alphabet, 1 + (get_byte(b, i) % 32), 1);
    end loop;
    exit when not exists (select 1 from public.invite_codes where code = c);
  end loop;
  return c;
end $$;
revoke execute on function public.cg_new_invite_code() from public, anon, authenticated;

-- 5) Ana kod kaldırıldı: check_invite_code sadece gerçek, kullanılmamış kodları kabul eder
create or replace function public.check_invite_code(p_code text)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.invite_codes
                 where code = upper(trim(coalesce(p_code, ''))) and used_by is null and used_at is null);
$$;
revoke all on function public.check_invite_code(text) from public;
grant execute on function public.check_invite_code(text) to anon, authenticated;

-- 6) Kayıt: geçerli davet kodu ZORUNLU (boş kod ve CRW-MASTER reddedilir)
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  v_code  text := upper(trim(coalesce(new.raw_user_meta_data->>'invited_by', '')));
  v_pcode text := upper(trim(coalesce(new.raw_user_meta_data->>'invite_code', '')));
  i int;
begin
  if v_code = '' then
    raise exception 'INVITE_INVALID: davet kodu gerekli';
  end if;
  update public.invite_codes
     set used_by = new.id, used_at = now()
   where code = v_code and used_by is null and used_at is null;
  if not found then
    raise exception 'INVITE_INVALID: davet kodu gecersiz veya kullanilmis';
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
    v_code,
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
revoke execute on function public.handle_new_user() from public, anon, authenticated;
$mig$;
execute $t$
create temp table _r(step text, ok text);
grant all on _r to public;
insert into public.invite_codes (code, created_by) values ('CRW-DRYRN1', null);
insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at) values
 ('00000000-0000-0000-0000-000000000000','d1111111-0000-0000-0000-000000000001','authenticated','authenticated','sc1@example.invalid','{"username":"sc1","invited_by":"crw-dryrn1"}',now(),now());
insert into _r select '01 signup works, new codes', (select string_agg(code, ' ') from public.invite_codes where created_by='d1111111-0000-0000-0000-000000000001');
insert into _r select '02 new code format ok', (select (bool_and(code ~ '^CRW-[A-HJ-NP-Z2-9]{6}$'))::text from public.invite_codes where created_by='d1111111-0000-0000-0000-000000000001');
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"d1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into public.places (id, cat, name, city) values ('dryrun-sc-1','food','SC','Seoul');
  reset role;
  insert into _r values ('03 user adds place (trigger runs)', 'works');
exception when others then reset role; insert into _r values ('03 user adds place (trigger runs)', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"d1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into public.comments (place_id, username, text) values ('dryrun-sc-1','sc1','merhaba');
  reset role;
  insert into _r values ('04 user comments (trigger runs)', 'works');
exception when others then reset role; insert into _r values ('04 user comments (trigger runs)', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"d1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  update public.profiles set username='sc1b', role='admin' where id='d1111111-0000-0000-0000-000000000001';
  reset role;
  insert into _r values ('05 user edits own profile (trigger runs)', 'works');
exception when others then reset role; insert into _r values ('05 user edits own profile (trigger runs)', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"d1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into public.reports (target_type, target_id, reason) values ('place','dryrun-sc-1','spam');
  reset role;
  insert into _r values ('06 user reports place (trigger runs)', 'works');
exception when others then reset role; insert into _r values ('06 user reports place (trigger runs)', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"d1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  perform count(*) from public.comments;
  reset role;
  insert into _r values ('07 user reads comments (rule uses cg_is_admin)', 'works');
exception when others then reset role; insert into _r values ('07 user reads comments (rule uses cg_is_admin)', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"d1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  perform public.cg_is_admin();
  reset role;
  insert into _r values ('08 user calls cg_is_admin', 'works');
exception when others then reset role; insert into _r values ('08 user calls cg_is_admin', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  set local role anon;
  perform public.cg_is_admin();
  reset role;
  insert into _r values ('09 anon calls cg_is_admin', 'works');
exception when others then reset role; insert into _r values ('09 anon calls cg_is_admin', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"d1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  perform public.handle_new_user();
  reset role;
  insert into _r values ('10 user calls handle_new_user', 'works');
exception when others then reset role; insert into _r values ('10 user calls handle_new_user', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  set local role anon;
  perform public.cg_new_invite_code();
  reset role;
  insert into _r values ('11 anon calls cg_new_invite_code', 'works');
exception when others then reset role; insert into _r values ('11 anon calls cg_new_invite_code', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  set local role anon;
  perform public.check_invite_code('CRW-XXXXX');
  reset role;
  insert into _r values ('12 anon check_invite_code (signup screen)', 'works');
exception when others then reset role; insert into _r values ('12 anon check_invite_code (signup screen)', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  
  insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at) values ('00000000-0000-0000-0000-000000000000', gen_random_uuid(), 'authenticated','authenticated','m@example.invalid',jsonb_build_object('invited_by','CRW-MASTER'), now(), now());
  reset role;
  insert into _r values ('15 signup with CRW-MASTER (expect denied)', 'works');
exception when others then reset role; insert into _r values ('15 signup with CRW-MASTER (expect denied)', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  
  insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at) values ('00000000-0000-0000-0000-000000000000', gen_random_uuid(), 'authenticated','authenticated','n@example.invalid','{}', now(), now());
  reset role;
  insert into _r values ('16 signup without code (expect denied)', 'works');
exception when others then reset role; insert into _r values ('16 signup without code (expect denied)', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  
  insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at) values ('00000000-0000-0000-0000-000000000000', gen_random_uuid(), 'authenticated','authenticated','r@example.invalid',jsonb_build_object('invited_by','CRW-DRYRN1'), now(), now());
  reset role;
  insert into _r values ('17 reuse the used code (expect denied)', 'works');
exception when others then reset role; insert into _r values ('17 reuse the used code (expect denied)', 'denied (' || sqlstate || ')'); end $x$;
insert into _r select '18 check_invite_code(CRW-MASTER)', public.check_invite_code('CRW-MASTER')::text;
insert into _r select '19 check_invite_code(new user code)', public.check_invite_code((select code from public.invite_codes where created_by='d1111111-0000-0000-0000-000000000001' limit 1))::text;
insert into _r select '13 profile: name changed, role NOT admin', (select username||' / '||coalesce(role,'-') from public.profiles where id='d1111111-0000-0000-0000-000000000001');
insert into _r select '14 search_path set', (select string_agg(proname||'='||array_to_string(proconfig, ','), ' ') from pg_proc where pronamespace='public'::regnamespace and proname in ('cg_is_system','cg_is_server'));
$t$;
select string_agg(step||' = '||ok, E'\n') into res from _r;
raise exception 'DRYRUN RESULTS (rolled back):%', E'\n'||res;
end $outer$;
