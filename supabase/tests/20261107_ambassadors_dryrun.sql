-- KURU ÇALIŞTIRMA: hiçbir şey kaydedilmez, sonunda sonuçları hata mesajı olarak gösterir.
do $outer$
declare res text;
begin
execute $mig$-- ════════════════════════════════════════════════════════════════════════════
-- CrewGuide — Şehir elçileri (7 Kasım 2026)
-- Elçi (profiles.role = 'ambassador') = görünmez yardımcı moderatör, tüm şehirlerde:
--  • Onaysız yer ekler (zaten vardı) • Her yeri düzenler (fotoğraf dahil)
--  • Önerileri onaylar / reddeder • Yerleri gizler / gösterir
--  • Şikayetleri görür ve yönetir, yorumları gizler
--  • YAPAMAZ: yeri kalıcı silme, kullanıcı silme/devre dışı bırakma, davet yönetimi, rol verme
-- Elçiyi sadece admin atar (admin panelindeki kullanıcı listesinden).
-- Ek: profiller artık sadece giriş yapmış kullanıcılarca okunabilir (eskiden herkese açıktı).
-- DÜZELTME: fotoğraf yükleme kuralı (20261107_photos_lockdown) dosya adı yerine yer adına bakıyordu → hiç yükleme yapılamıyordu.
-- Tekrar çalıştırmak güvenlidir.
-- ════════════════════════════════════════════════════════════════════════════

-- 1) Rol değerleri
update public.profiles set role = 'user' where role is null or role not in ('user', 'ambassador', 'admin');
alter table public.profiles drop constraint if exists profiles_role_check;
alter table public.profiles add constraint profiles_role_check check (role in ('user', 'ambassador', 'admin'));

-- 2) Profiller: okuma sadece giriş yapmışlar; admin başkasının profilini (rolünü) güncelleyebilir
drop policy if exists "Admin profiles görebilir" on public.profiles;
drop policy if exists "Anyone can read profiles" on public.profiles;
drop policy if exists "Herkes profil görebilir" on public.profiles;
drop policy if exists "cg profiles read" on public.profiles;
create policy "cg profiles read" on public.profiles
  for select to authenticated using (true);
revoke select on public.profiles from anon;

drop policy if exists "cg admin update profiles" on public.profiles;
create policy "cg admin update profiles" on public.profiles
  for update to authenticated using (public.cg_is_admin()) with check (public.cg_is_admin());

-- 3) Yerler: elçi her yeri güncelleyebilir (silme yine sadece sahibi/admin)
drop policy if exists "cg trusted update places" on public.places;
create policy "cg trusted update places" on public.places
  for update to authenticated using (public.cg_is_trusted()) with check (public.cg_is_trusted());

create or replace function public.cg_places_before_update()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if public.cg_is_server() or public.cg_is_system() then
    return new;
  end if;
  -- Puan ve bildirim alanları: admin dahil kimse elle değiştiremez
  new.rating       := old.rating;
  new.rating_count := old.rating_count;
  new.likes        := old.likes;
  new.push_sent_at := old.push_sent_at;
  if public.cg_is_admin() then
    return new;
  end if;
  -- Yerin sahibi elçi tarafından değiştirilemez
  new.user_id := old.user_id;
  if public.cg_is_trusted() then
    return new;   -- elçi: onay durumu ve gizlilik dahil düzenleyebilir
  end if;
  -- Normal kullanıcı (kendi yeri): onay durumu değişmez, gizlenen yer açılamaz
  new.status := old.status;
  if old.is_hidden and not new.is_hidden then
    new.is_hidden := true;
  end if;
  return new;
end $$;
revoke execute on function public.cg_places_before_update() from public, anon, authenticated;

-- 4) Yorumlar: elçi gizli yorumları görür ve başkasının yorumunu sadece gizleyebilir/gösterebilir
drop policy if exists "cg read visible comments" on public.comments;
create policy "cg read visible comments" on public.comments
  for select to authenticated
  using (not is_hidden or user_id = auth.uid() or public.cg_is_trusted());

drop policy if exists "cg trusted update comments" on public.comments;
create policy "cg trusted update comments" on public.comments
  for update to authenticated using (public.cg_is_trusted()) with check (public.cg_is_trusted());

create or replace function public.cg_comments_protect()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if public.cg_is_server() or public.cg_is_system() or public.cg_is_admin() then
    return new;
  end if;
  if tg_op = 'INSERT' then
    new.user_id := auth.uid();         -- başkası adına yorum yazılamaz
    new.is_hidden := false;
    return new;
  end if;
  if old.user_id is distinct from auth.uid() then
    if public.cg_is_trusted() then
      -- Elçi başkasının yorumunda sadece görünürlüğü değiştirebilir
      new.text       := old.text;
      new.stars      := old.stars;
      new.username   := old.username;
      new.created_at := old.created_at;
      new.user_id    := old.user_id;
      new.place_id   := old.place_id;
      return new;
    end if;
    return old;  -- (RLS zaten engeller; ek güvence)
  end if;
  -- Kendi yorumu
  new.user_id := old.user_id;
  new.place_id := old.place_id;
  if old.is_hidden and not public.cg_is_trusted() then new.is_hidden := true; end if;  -- gizlenen yorum sahibince açılamaz
  return new;
end $$;
revoke execute on function public.cg_comments_protect() from public, anon, authenticated;

-- 5) Şikayetler: elçi görür ve kapatır (silme sadece admin)
drop policy if exists "cg read own or admin reports" on public.reports;
create policy "cg read own or admin reports" on public.reports
  for select to authenticated
  using (reporter_id = auth.uid() or public.cg_is_trusted());

drop policy if exists "cg admin update reports" on public.reports;
create policy "cg admin update reports" on public.reports
  for update to authenticated using (public.cg_is_trusted()) with check (public.cg_is_trusted());

-- 6) Fotoğraflar: elçi her yere fotoğraf ekleyebilir / kaldırabilir
drop policy if exists "cg place photos upload" on storage.objects;
create policy "cg place photos upload" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'place-photos'
    and lower(storage.extension(objects.name)) in ('jpg', 'jpeg', 'png', 'webp')
    and exists (
      select 1 from public.places p
       -- DİKKAT: places tablosunda da "name" kolonu var → dosya adı mutlaka objects.name diye yazılmalı
       -- (önceki sürümde p.name'e bağlanıyordu ve hiçbir fotoğraf yüklenemiyordu)
       where p.id = (storage.foldername(objects.name))[1]
         and (p.user_id = auth.uid() or public.cg_is_trusted())
    )
  );

drop policy if exists "cg place photos delete" on storage.objects;
create policy "cg place photos delete" on storage.objects
  for delete to authenticated
  using (bucket_id = 'place-photos' and (owner_id = auth.uid()::text or public.cg_is_trusted()));

drop policy if exists "cg photos insert own place" on public.photos;
create policy "cg photos insert own place" on public.photos
  for insert to authenticated
  with check (
    exists (select 1 from public.places p
             where p.id = place_id and (p.user_id = auth.uid() or public.cg_is_trusted()))
    and starts_with(url, 'https://nuebqtzeirpyyxtoptlp.supabase.co/storage/v1/object/public/place-photos/' || place_id || '/')
  );

drop policy if exists "cg photos delete own place" on public.photos;
create policy "cg photos delete own place" on public.photos
  for delete to authenticated
  using (exists (select 1 from public.places p
                  where p.id = place_id and (p.user_id = auth.uid() or public.cg_is_trusted())));
$mig$;
execute $t$
create temp table _r(n serial, step text, ok text);
grant all on _r to public;
grant all on sequence _r_n_seq to public;
insert into public.invite_codes (code, created_by) values ('CRW-AMBT01', null), ('CRW-AMBT02', null), ('CRW-AMBT03', null), ('CRW-AMBT04', null);
insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at) values
 ('00000000-0000-0000-0000-000000000000','e0000000-0000-0000-0000-00000000000a','authenticated','authenticated','adm@example.invalid', jsonb_build_object('username','t_admin','invited_by','CRW-AMBT01'), now(), now()),
 ('00000000-0000-0000-0000-000000000000','e0000000-0000-0000-0000-0000000000a2','authenticated','authenticated','amb@example.invalid', jsonb_build_object('username','t_amb','invited_by','CRW-AMBT02'), now(), now()),
 ('00000000-0000-0000-0000-000000000000','e0000000-0000-0000-0000-000000000001','authenticated','authenticated','u1@example.invalid', jsonb_build_object('username','t_u1','invited_by','CRW-AMBT03'), now(), now()),
 ('00000000-0000-0000-0000-000000000000','e0000000-0000-0000-0000-000000000002','authenticated','authenticated','u2@example.invalid', jsonb_build_object('username','t_u2','invited_by','CRW-AMBT04'), now(), now());
update public.profiles set role = 'admin' where id = 'e0000000-0000-0000-0000-00000000000a';
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-00000000000a","role":"authenticated"}', true); set local role authenticated;
  update public.profiles set role = 'ambassador' where id = 'e0000000-0000-0000-0000-0000000000a2';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('a1', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '01 admin makes ambassador → ambassador', (select role from public.profiles where id = 'e0000000-0000-0000-0000-0000000000a2')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-0000000000a2","role":"authenticated"}', true); set local role authenticated;
  update public.profiles set role = 'ambassador' where id = 'e0000000-0000-0000-0000-000000000001';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('a2', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '02 ambassador cannot promote others → user', (select role from public.profiles where id = 'e0000000-0000-0000-0000-000000000001')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  update public.profiles set role = 'ambassador' where id = 'e0000000-0000-0000-0000-000000000001';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('a3', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '03 user cannot promote self → user', (select role from public.profiles where id = 'e0000000-0000-0000-0000-000000000001')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-00000000000a","role":"authenticated"}', true); set local role authenticated;
  update public.profiles set role = 'superuser' where id = 'e0000000-0000-0000-0000-0000000000a2';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('04b invalid role write (expect denied 23514)', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '04 invalid role rejected → ambassador', (select role from public.profiles where id = 'e0000000-0000-0000-0000-0000000000a2')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into public.places (id, cat, name, city) values ('dry-amb-p1','food','Oneri','Seoul');
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('b1', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '05 user suggestion → pending/true', (select status || '/' || is_hidden from public.places where id = 'dry-amb-p1')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  update public.places set status = 'approved', is_hidden = false where id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('b2', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '06 owner cannot self-approve → pending/true', (select status || '/' || is_hidden from public.places where id = 'dry-amb-p1')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-0000000000a2","role":"authenticated"}', true); set local role authenticated;
  update public.places set status = 'approved', is_hidden = false where id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('b3', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '07 ambassador approves → approved/false', (select status || '/' || is_hidden from public.places where id = 'dry-amb-p1')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-0000000000a2","role":"authenticated"}', true); set local role authenticated;
  update public.places set name = 'Duzeltildi', user_id = 'e0000000-0000-0000-0000-0000000000a2', rating = 5 where id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('b4', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '08 ambassador edits name, owner/rating kept → Duzeltildi/true/0', (select name || '/' || (user_id = 'e0000000-0000-0000-0000-000000000001') || '/' || rating from public.places where id = 'dry-amb-p1')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-000000000002","role":"authenticated"}', true); set local role authenticated;
  update public.places set name = 'Hack' where id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('b5', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '09 other user cannot edit → Duzeltildi', (select name from public.places where id = 'dry-amb-p1')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-0000000000a2","role":"authenticated"}', true); set local role authenticated;
  update public.places set is_hidden = true where id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('b6', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '10 ambassador hides → true', (select is_hidden from public.places where id = 'dry-amb-p1')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-0000000000a2","role":"authenticated"}', true); set local role authenticated;
  delete from public.places where id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('b7', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '11 ambassador cannot delete → 1', (select count(*) from public.places where id = 'dry-amb-p1')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into public.comments (place_id, username, text) values ('dry-amb-p1','t_u1','orijinal');
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('c1', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-0000000000a2","role":"authenticated"}', true); set local role authenticated;
  update public.comments set is_hidden = true, text = 'degisti' where place_id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('c2', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '12 ambassador hides comment, text kept → true/orijinal', (select is_hidden || '/' || text from public.comments where place_id = 'dry-amb-p1')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-000000000002","role":"authenticated"}', true); set local role authenticated;
  insert into _r(step, ok) select '13 other user sees hidden comment → 0', count(*)::text from public.comments where place_id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('c3', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-0000000000a2","role":"authenticated"}', true); set local role authenticated;
  insert into _r(step, ok) select '14 ambassador sees hidden comment → 1', count(*)::text from public.comments where place_id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('c4', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-000000000002","role":"authenticated"}', true); set local role authenticated;
  insert into public.reports (target_type, target_id, reason) values ('place','dry-amb-p1','spam');
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('d1', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-0000000000a2","role":"authenticated"}', true); set local role authenticated;
  insert into _r(step, ok) select '15 ambassador reads reports → >=1', (count(*) >= 1)::text from public.reports where target_id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('d2', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-0000000000a2","role":"authenticated"}', true); set local role authenticated;
  update public.reports set status = 'resolved', resolved_at = now() where target_id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('d3', 'denied (' || sqlstate || ')'); end $x$;
insert into _r(step, ok) select '16 ambassador resolves report → resolved', (select string_agg(distinct status, ',') from public.reports where target_id = 'dry-amb-p1')::text;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into _r(step, ok) select '17 other user cannot read others reports → 0', count(*)::text from public.reports where target_id = 'dry-amb-p1';
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('d4', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into storage.objects (bucket_id, name, owner_id) values ('place-photos','dry-amb-p1/own.jpg','e0000000-0000-0000-0000-000000000001'); insert into _r(step, ok) values ('18a owner uploads photo to own place', 'works');
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('18a owner uploads photo to own place', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-0000000000a2","role":"authenticated"}', true); set local role authenticated;
  insert into storage.objects (bucket_id, name, owner_id) values ('place-photos','dry-amb-p1/amb.jpg','e0000000-0000-0000-0000-0000000000a2'); insert into _r(step, ok) values ('18 ambassador uploads photo to others place', 'works');
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('18 ambassador uploads photo to others place', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-000000000002","role":"authenticated"}', true); set local role authenticated;
  insert into storage.objects (bucket_id, name, owner_id) values ('place-photos','dry-amb-p1/u2.jpg','e0000000-0000-0000-0000-000000000002'); insert into _r(step, ok) values ('19 other user uploads to others place (expect denied)', 'works');
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('19 other user uploads to others place (expect denied)', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  set local role anon;
  perform count(*) from public.profiles; insert into _r(step, ok) values ('20 anon reads profiles (expect denied)', 'works');
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('20 anon reads profiles (expect denied)', 'denied (' || sqlstate || ')'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"e0000000-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into _r(step, ok) select '21 user reads profiles → >0', (count(*) > 0)::text from public.profiles;
  reset role;
exception when others then reset role; insert into _r(step, ok) values ('f2', 'denied (' || sqlstate || ')'); end $x$;
$t$;
select string_agg(step||' = '||ok, E'\n' order by n) into res from _r;
raise exception 'DRYRUN RESULTS (rolled back):%', E'\n'||res;
end $outer$;
