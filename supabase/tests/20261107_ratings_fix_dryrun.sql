-- KURU ÇALIŞTIRMA: hiçbir şey kaydedilmez, sonunda sonuçları hata mesajı olarak gösterir.
do $outer$
declare res text;
begin
execute $mig$-- ════════════════════════════════════════════════════════════════════════════
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
$mig$;
execute $t$
create temp table _r(step text, ok text);
grant all on _r to public;
-- test kullanıcıları
insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at) values
 ('00000000-0000-0000-0000-000000000000','a1111111-0000-0000-0000-000000000001','authenticated','authenticated','owner@example.invalid','{"username":"owner","invited_by":"CRW-MASTER"}',now(),now()),
 ('00000000-0000-0000-0000-000000000000','a2222222-0000-0000-0000-000000000002','authenticated','authenticated','rater@example.invalid','{"username":"rater","invited_by":"CRW-MASTER"}',now(),now()),
 ('00000000-0000-0000-0000-000000000000','a3333333-0000-0000-0000-000000000003','authenticated','authenticated','rater2@example.invalid','{"username":"rater2","invited_by":"CRW-MASTER"}',now(),now());
insert into _r select 'backfill mismatches', (select count(*)::text from public.places p where coalesce(p.rating_count,0) <> (select count(*) from public.ratings r where r.place_id=p.id));

-- sahibi (owner) yer ekler; puan/beğeni alanlarını şişirmeye çalışır
select set_config('request.jwt.claims', '{"sub":"a1111111-0000-0000-0000-000000000001","role":"authenticated"}', true);
set local role authenticated;
insert into public.places (id, cat, name, city, rating, rating_count, likes) values ('dryrun-rt-1','food','Dryrun Yer','Seoul', 5, 99, 50);
reset role;
insert into _r select 'insert forces zeros', (select rating||'/'||rating_count||'/'||likes from public.places where id='dryrun-rt-1');
update public.places set status='approved', is_hidden=false where id='dryrun-rt-1';

-- rater 4 yıldız verir
select set_config('request.jwt.claims', '{"sub":"a2222222-0000-0000-0000-000000000002","role":"authenticated"}', true);
set local role authenticated;
insert into public.ratings (place_id, user_id, stars) values ('dryrun-rt-1','a2222222-0000-0000-0000-000000000002',4)
  on conflict (place_id, user_id) do update set stars = excluded.stars;
reset role;
insert into _r select 'first rating 4', (select rating||' / '||rating_count from public.places where id='dryrun-rt-1');

-- rater puanını 2'ye günceller (uygulamanın yaptığı upsert)
select set_config('request.jwt.claims', '{"sub":"a2222222-0000-0000-0000-000000000002","role":"authenticated"}', true);
set local role authenticated;
insert into public.ratings (place_id, user_id, stars) values ('dryrun-rt-1','a2222222-0000-0000-0000-000000000002',2)
  on conflict (place_id, user_id) do update set stars = excluded.stars;
reset role;
insert into _r select 'update to 2', (select rating||' / '||rating_count from public.places where id='dryrun-rt-1');

-- rater2 5 verir → ortalama 3.5
select set_config('request.jwt.claims', '{"sub":"a3333333-0000-0000-0000-000000000003","role":"authenticated"}', true);
set local role authenticated;
insert into public.ratings (place_id, user_id, stars) values ('dryrun-rt-1','a3333333-0000-0000-0000-000000000003',5)
  on conflict (place_id, user_id) do update set stars = excluded.stars;
reset role;
insert into _r select 'second user 5 → avg', (select rating||' / '||rating_count from public.places where id='dryrun-rt-1');

-- rater2 başkası adına oy veremez
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"a3333333-0000-0000-0000-000000000003","role":"authenticated"}', true);
  set local role authenticated;
  insert into public.ratings (place_id, user_id, stars) values ('dryrun-rt-1','a1111111-0000-0000-0000-000000000001',5);
  reset role;
  insert into _r values ('rate as someone else blocked','NO (BUG)');
exception when others then reset role; insert into _r values ('rate as someone else blocked','yes'); end $x$;

-- sahibi puanı elle değiştirmeye çalışır
select set_config('request.jwt.claims', '{"sub":"a1111111-0000-0000-0000-000000000001","role":"authenticated"}', true);
set local role authenticated;
update public.places set rating=5, rating_count=999, likes=77, name='Dryrun Yer 2' where id='dryrun-rt-1';
reset role;
insert into _r select 'owner cannot fake rating (name still editable)', (select rating||' / '||rating_count||' / likes '||likes||' / '||name from public.places where id='dryrun-rt-1');

-- rater kendi oyunu siler → sadece rater2'nin 5'i kalır
select set_config('request.jwt.claims', '{"sub":"a2222222-0000-0000-0000-000000000002","role":"authenticated"}', true);
set local role authenticated;
delete from public.ratings where place_id='dryrun-rt-1' and user_id='a2222222-0000-0000-0000-000000000002';
insert into _r select 'rater sees ratings', (select count(*)::text from public.ratings where place_id='dryrun-rt-1');
reset role;
insert into _r select 'after delete', (select rating||' / '||rating_count from public.places where id='dryrun-rt-1');

-- anon okuyamaz
do $x$ begin
  set local role anon;
  perform 1 from public.ratings limit 1;
  reset role;
  insert into _r values ('anon read blocked','NO (BUG)');
exception when others then reset role; insert into _r values ('anon read blocked','yes'); end $x$;

-- kullanıcı silinince oy anonim kalır, ortalama bozulmaz
delete from auth.users where id='a3333333-0000-0000-0000-000000000003';
insert into _r select 'after user delete', (select rating||' / '||rating_count from public.places where id='dryrun-rt-1');
$t$;
select string_agg(step||' = '||ok, E'\n') into res from _r;
raise exception 'DRYRUN RESULTS (rolled back):%', E'\n'||res;
end $outer$;
