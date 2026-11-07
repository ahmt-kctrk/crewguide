-- ════════════════════════════════════════════════════════════════════════════
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
