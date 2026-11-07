-- KURU ÇALIŞTIRMA: hiçbir şey kaydedilmez, sonunda sonuçları hata mesajı olarak gösterir.
do $outer$
declare res text;
begin
execute $mig$-- ════════════════════════════════════════════════════════════════════════════
-- CrewGuide — Fotoğraf güvenliği (7 Kasım 2026)
--  • place-photos deposu: eskiden GİRİŞ YAPMAMIŞ biri bile her türden, her boyutta dosya
--    yükleyebiliyordu. Artık: sadece giriş yapmış kullanıcı, sadece KENDİ yerinin klasörüne
--    (admin her yere), sadece jpg/jpeg/png/webp, en fazla 5 MB.
--  • photos tablosu: eskiden herkes herhangi bir yere herhangi bir adresle fotoğraf
--    ekleyebiliyordu. Artık: sadece yerin sahibi/admin, sadece kendi depomuzdaki o yerin
--    klasörüne işaret eden adresle. Sahibi/admin fotoğraf kaydını silebilir.
--  • Okuma: sadece giriş yapmış kullanıcılar listeleyebilir (fotoğraf dosyaları herkese açık
--    adresle yine görünür — uygulamanın çalışması için gerekli).
-- Tekrar çalıştırmak güvenlidir.
-- ════════════════════════════════════════════════════════════════════════════

-- 1) Depo sınırları
update storage.buckets
   set file_size_limit = 5242880,
       allowed_mime_types = array['image/jpeg', 'image/png', 'image/webp']
 where id = 'place-photos';

-- 2) Depo politikaları
drop policy if exists "Herkes yukleyebilir" on storage.objects;
drop policy if exists "Herkes gorebilir" on storage.objects;
drop policy if exists "cg place photos read" on storage.objects;
drop policy if exists "cg place photos upload" on storage.objects;
drop policy if exists "cg place photos delete" on storage.objects;

create policy "cg place photos read" on storage.objects
  for select to authenticated
  using (bucket_id = 'place-photos');

create policy "cg place photos upload" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'place-photos'
    and lower(storage.extension(name)) in ('jpg', 'jpeg', 'png', 'webp')
    and exists (
      select 1 from public.places p
       where p.id = (storage.foldername(name))[1]
         and (p.user_id = auth.uid() or public.cg_is_admin())
    )
  );

create policy "cg place photos delete" on storage.objects
  for delete to authenticated
  using (
    bucket_id = 'place-photos'
    and (owner_id = auth.uid()::text or public.cg_is_admin())
  );

-- 3) photos tablosu
alter table public.photos enable row level security;

drop policy if exists "Herkes ekleyebilir" on public.photos;
drop policy if exists "Herkes gorebilir" on public.photos;
drop policy if exists "Herkes okuyabilir" on public.photos;
drop policy if exists "cg photos read" on public.photos;
drop policy if exists "cg photos insert own place" on public.photos;
drop policy if exists "cg photos delete own place" on public.photos;

create policy "cg photos read" on public.photos
  for select to authenticated using (true);

create policy "cg photos insert own place" on public.photos
  for insert to authenticated
  with check (
    exists (select 1 from public.places p
             where p.id = place_id and (p.user_id = auth.uid() or public.cg_is_admin()))
    and starts_with(url, 'https://nuebqtzeirpyyxtoptlp.supabase.co/storage/v1/object/public/place-photos/' || place_id || '/')
  );

create policy "cg photos delete own place" on public.photos
  for delete to authenticated
  using (
    exists (select 1 from public.places p
             where p.id = place_id and (p.user_id = auth.uid() or public.cg_is_admin()))
  );

revoke all on public.photos from anon;
$mig$;
execute $t$
create temp table _r(step text, ok text);
grant all on _r to public;
insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at) values
 ('00000000-0000-0000-0000-000000000000','c1111111-0000-0000-0000-000000000001','authenticated','authenticated','ph1@example.invalid','{"username":"ph1","invited_by":"CRW-MASTER"}',now(),now()),
 ('00000000-0000-0000-0000-000000000000','c2222222-0000-0000-0000-000000000002','authenticated','authenticated','ph2@example.invalid','{"username":"ph2","invited_by":"CRW-MASTER"}',now(),now());
insert into _r select 'bucket limits', (select file_size_limit||' / '||array_to_string(allowed_mime_types, ',') from storage.buckets where id='place-photos');
select set_config('request.jwt.claims', '{"sub":"c1111111-0000-0000-0000-000000000001","role":"authenticated"}', true);
set local role authenticated;
insert into public.places (id, cat, name, city) values ('dryrun-ph-1','food','Foto Test 1','Seoul');
reset role;
select set_config('request.jwt.claims', '{"sub":"c2222222-0000-0000-0000-000000000002","role":"authenticated"}', true);
set local role authenticated;
insert into public.places (id, cat, name, city) values ('dryrun-ph-2','food','Foto Test 2','Seoul');
reset role;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"c1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into storage.objects (bucket_id, name, owner_id) values ('place-photos','dryrun-ph-1/a.jpg','c1111111-0000-0000-0000-000000000001');
  reset role;
  insert into _r values ('1 owner uploads jpg to own place (expect ALLOWED)', 'ALLOWED');
exception when others then reset role; insert into _r values ('1 owner uploads jpg to own place (expect ALLOWED)', 'blocked'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"c1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into storage.objects (bucket_id, name, owner_id) values ('place-photos','dryrun-ph-2/x.jpg','c1111111-0000-0000-0000-000000000001');
  reset role;
  insert into _r values ('2 upload to someone elses place (expect blocked)', 'ALLOWED');
exception when others then reset role; insert into _r values ('2 upload to someone elses place (expect blocked)', 'blocked'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"c1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into storage.objects (bucket_id, name, owner_id) values ('place-photos','dryrun-ph-1/evil.html','c1111111-0000-0000-0000-000000000001');
  reset role;
  insert into _r values ('3 upload .html to own place (expect blocked)', 'ALLOWED');
exception when others then reset role; insert into _r values ('3 upload .html to own place (expect blocked)', 'blocked'); end $x$;
do $x$ begin
  set local role anon;
  insert into storage.objects (bucket_id, name) values ('place-photos','dryrun-ph-1/anon.jpg');
  reset role;
  insert into _r values ('4 anonymous upload (expect blocked)', 'ALLOWED');
exception when others then reset role; insert into _r values ('4 anonymous upload (expect blocked)', 'blocked'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"c1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into public.photos (place_id, url) values ('dryrun-ph-1','https://nuebqtzeirpyyxtoptlp.supabase.co/storage/v1/object/public/place-photos/dryrun-ph-1/a.jpg');
  reset role;
  insert into _r values ('5 photo row own place, own storage url (expect ALLOWED)', 'ALLOWED');
exception when others then reset role; insert into _r values ('5 photo row own place, own storage url (expect ALLOWED)', 'blocked'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"c1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into public.photos (place_id, url) values ('dryrun-ph-1','https://evil.example/x.jpg');
  reset role;
  insert into _r values ('6 photo row with outside url (expect blocked)', 'ALLOWED');
exception when others then reset role; insert into _r values ('6 photo row with outside url (expect blocked)', 'blocked'); end $x$;
do $x$ begin
  perform set_config('request.jwt.claims', '{"sub":"c1111111-0000-0000-0000-000000000001","role":"authenticated"}', true); set local role authenticated;
  insert into public.photos (place_id, url) values ('dryrun-ph-2','https://nuebqtzeirpyyxtoptlp.supabase.co/storage/v1/object/public/place-photos/dryrun-ph-2/a.jpg');
  reset role;
  insert into _r values ('7 photo row on someone elses place (expect blocked)', 'ALLOWED');
exception when others then reset role; insert into _r values ('7 photo row on someone elses place (expect blocked)', 'blocked'); end $x$;
do $x$ begin
  set local role anon;
  insert into public.photos (place_id, url) values ('dryrun-ph-1','https://nuebqtzeirpyyxtoptlp.supabase.co/storage/v1/object/public/place-photos/dryrun-ph-1/b.jpg');
  reset role;
  insert into _r values ('8 anonymous photo row (expect blocked)', 'ALLOWED');
exception when others then reset role; insert into _r values ('8 anonymous photo row (expect blocked)', 'blocked'); end $x$;

select set_config('request.jwt.claims', '{"sub":"c2222222-0000-0000-0000-000000000002","role":"authenticated"}', true);
set local role authenticated;
delete from public.photos where place_id='dryrun-ph-1';
reset role;
insert into _r select '9 other user deletes photo row (expect 1 left)', (select count(*)::text from public.photos where place_id='dryrun-ph-1');
select set_config('request.jwt.claims', '{"sub":"c1111111-0000-0000-0000-000000000001","role":"authenticated"}', true);
set local role authenticated;
delete from public.photos where place_id='dryrun-ph-1';
reset role;
insert into _r select '10 owner deletes photo row (expect 0 left)', (select count(*)::text from public.photos where place_id='dryrun-ph-1');
insert into _r select '11 existing photos still listed', (select (count(*) > 0)::text from public.photos);
$t$;
select string_agg(step||' = '||ok, E'\n') into res from _r;
raise exception 'DRYRUN RESULTS (rolled back):%', E'\n'||res;
end $outer$;
