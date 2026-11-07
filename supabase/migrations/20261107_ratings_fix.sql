-- ════════════════════════════════════════════════════════════════════════════
-- CrewGuide — Puanlama düzeltmesi (7 Kasım 2026)
--  • places.rating / rating_count artık SUNUCUDA hesaplanır (ratings tetikleyicisi).
--    Eskiden istemci yazıyordu; yer sahibi olmayan kullanıcıda RLS yüzünden sessizce
--    başarısız oluyordu ve yer sahibi kendi puanını elle değiştirebiliyordu.
--  • rating / rating_count / likes alanlarını sadece sistem değiştirebilir.
--  • Yeni yer eklerken bu alanlar 0'dan başlar.
--  • ratings politikaları: sadece giriş yapmış kullanıcılar; herkes sadece kendi oyunu yazar/siler.
--  • Mevcut tüm yerlerin puanları bir kez yeniden hesaplanır.
-- Tekrar çalıştırmak güvenlidir.
-- ════════════════════════════════════════════════════════════════════════════

-- 1) Bir yerin ortalamasını ve oy sayısını yeniden hesapla
create or replace function public.cg_recalc_place_rating(p_place_id text)
returns void language plpgsql security definer set search_path = public as $$
begin
  perform set_config('cg.system', 'on', true);
  update public.places p
     set rating       = coalesce(x.avg, 0),
         rating_count = coalesce(x.cnt, 0)
    from (select round(avg(stars)::numeric, 1) as avg, count(*)::int as cnt
            from public.ratings where place_id = p_place_id) x
   where p.id = p_place_id
     and (p.rating is distinct from coalesce(x.avg, 0) or p.rating_count is distinct from coalesce(x.cnt, 0));
  perform set_config('cg.system', '', true);
end $$;
revoke all on function public.cg_recalc_place_rating(text) from public, anon, authenticated;

create or replace function public.cg_ratings_after_change()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op in ('UPDATE', 'DELETE') then
    perform public.cg_recalc_place_rating(old.place_id);
  end if;
  if tg_op in ('INSERT', 'UPDATE') and (tg_op = 'INSERT' or new.place_id is distinct from old.place_id or new.stars is distinct from old.stars) then
    perform public.cg_recalc_place_rating(new.place_id);
  end if;
  return null;
end $$;
revoke all on function public.cg_ratings_after_change() from public, anon, authenticated;

drop trigger if exists cg_ratings_after_change on public.ratings;
create trigger cg_ratings_after_change
  after insert or update or delete on public.ratings
  for each row execute function public.cg_ratings_after_change();

-- 2) Yer tetikleyicileri: puan/beğeni alanlarını sadece sistem değiştirebilir
create or replace function public.cg_places_before_update()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if public.cg_is_server() or public.cg_is_system() then
    return new;
  end if;
  -- Puan alanları: admin dahil kimse elle değiştiremez
  new.rating       := old.rating;
  new.rating_count := old.rating_count;
  new.likes        := old.likes;
  if public.cg_is_admin() then
    return new;
  end if;
  new.status  := old.status;
  new.user_id := old.user_id;
  if old.is_hidden and not new.is_hidden then
    new.is_hidden := true;
  end if;
  return new;
end $$;

create or replace function public.cg_places_before_insert()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if auth.role() = 'service_role' then
    return new;
  end if;
  new.rating       := 0;
  new.rating_count := 0;
  new.likes        := 0;
  if public.cg_is_trusted() then
    new.status := 'approved';
  else
    new.status := 'pending';
    new.is_hidden := true;
  end if;
  -- Kayıt sahibi her zaman isteği yapan kullanıcıdır
  if auth.uid() is not null then
    new.user_id := auth.uid();
  end if;
  return new;
end $$;

-- 3) ratings politikaları
alter table public.ratings enable row level security;

drop policy if exists "Herkes okuyabilir" on public.ratings;
drop policy if exists "cg ratings read" on public.ratings;
create policy "cg ratings read" on public.ratings
  for select to authenticated using (true);

drop policy if exists "Giriş yapan yazabilir" on public.ratings;
drop policy if exists "cg ratings insert own" on public.ratings;
create policy "cg ratings insert own" on public.ratings
  for insert to authenticated with check (user_id = auth.uid());

drop policy if exists "Kendi kaydını güncelleyebilir" on public.ratings;
drop policy if exists "cg ratings update own" on public.ratings;
create policy "cg ratings update own" on public.ratings
  for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "cg ratings delete own" on public.ratings;
create policy "cg ratings delete own" on public.ratings
  for delete to authenticated using (user_id = auth.uid() or public.cg_is_admin());

revoke all on public.ratings from anon;

-- 4) Mevcut tüm yerleri bir kez yeniden hesapla (beğeni sayısı kullanılmıyor → 0)
do $$
declare r record;
begin
  for r in select id from public.places loop
    perform public.cg_recalc_place_rating(r.id);
  end loop;
  perform set_config('cg.system', 'on', true);
  update public.places set likes = 0 where coalesce(likes, 0) <> 0;
  perform set_config('cg.system', '', true);
end $$;
