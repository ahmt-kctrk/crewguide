-- ════════════════════════════════════════════════════════════════════════════
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
