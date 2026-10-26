-- ════════════════════════════════════════════════════════════════════════════
-- CrewGuide — Mekan önerisi + admin onay sistemi
-- Supabase Dashboard → SQL Editor → bu dosyanın tamamını yapıştır → Run
-- Tekrar çalıştırmak güvenlidir (idempotent).
-- ════════════════════════════════════════════════════════════════════════════

-- 1) Durum kolonu: pending (onay bekliyor) / approved (yayında) / rejected (reddedildi)
--    Mevcut tüm yerler 'approved' olarak işaretlenir.
alter table public.places add column if not exists status text not null default 'approved';
alter table public.places drop constraint if exists places_status_check;
alter table public.places add constraint places_status_check
  check (status in ('pending', 'approved', 'rejected'));
create index if not exists places_status_pending_idx on public.places (status) where status = 'pending';

-- 2) Yetki yardımcıları
create or replace function public.cg_is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select coalesce((auth.jwt() ->> 'email') = 'ahmtkctrk@gmail.com', false)
      or exists (select 1 from public.profiles where id::text = auth.uid()::text and role = 'admin');
$$;

-- Admin + şehir elçisi (profiles.role = 'ambassador'): ekledikleri yer onaysız yayınlanır
create or replace function public.cg_is_trusted()
returns boolean language sql stable security definer set search_path = public as $$
  select public.cg_is_admin()
      or exists (select 1 from public.profiles where id::text = auth.uid()::text and role = 'ambassador');
$$;

-- 3) Yeni yer eklenirken: güvenilir değilse zorla "onay bekliyor + gizli"
--    (Uygulama tarafı da aynısını yapıyor ama asıl güvence burası.)
create or replace function public.cg_places_before_insert()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if auth.role() = 'service_role' then
    return new;
  end if;
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

drop trigger if exists cg_places_before_insert on public.places;
create trigger cg_places_before_insert
  before insert on public.places
  for each row execute function public.cg_places_before_insert();

-- 4) Güncellemede: sadece admin onay durumunu değiştirebilir / gizliyi açabilir.
--    Sahip kendi yerini gizleyebilir (silme) ama tekrar açamaz; sahipliği değiştiremez.
create or replace function public.cg_places_before_update()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if auth.role() = 'service_role' or public.cg_is_admin() then
    return new;
  end if;
  new.status  := old.status;
  new.user_id := old.user_id;
  if old.is_hidden and not new.is_hidden then
    new.is_hidden := true;
  end if;
  return new;
end $$;

drop trigger if exists cg_places_before_update on public.places;
create trigger cg_places_before_update
  before update on public.places
  for each row execute function public.cg_places_before_update();

-- 5) Kullanıcı kendi onay bekleyen önerilerini "Benim yerlerim"de görebilsin.
--    (RLS kapalıysa etkisizdir; açıksa mevcut politikalara EK izin verir.)
drop policy if exists "cg owner can read own places" on public.places;
create policy "cg owner can read own places" on public.places
  for select to authenticated
  using (user_id::text = auth.uid()::text);

-- 6) Kontrol: RLS açık mı? (relrowsecurity = true olmalı)
select relname, relrowsecurity from pg_class where relname in ('places', 'profiles');

-- Bir arkadaşını şehir elçisi yapmak için (kullanıcı adını değiştir):
-- update public.profiles set role = 'ambassador' where username = 'kullanici_adi';
