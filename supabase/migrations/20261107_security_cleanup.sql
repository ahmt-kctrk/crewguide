-- ════════════════════════════════════════════════════════════════════════════
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
