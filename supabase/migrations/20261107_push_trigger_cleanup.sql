-- ════════════════════════════════════════════════════════════════════════════
-- CrewGuide — Yer bildirimleri temizliği (7 Kasım 2026)
--  • Eski iki webhook tetikleyicisi kaldırılır:
--      on_place_insert   → Authorization başlığında service_role anahtarı AÇIK METİN duruyordu
--      notify-new-place  → yetkisiz çağrı (send-push 403 dönüyordu)
--  • Tek kaynak: yer YAYINA GİRDİĞİNDE (onaylı eklendiğinde ya da admin onayladığında)
--    veritabanı send-push'u çağırır. Başlıkta sadece herkese açık anon anahtar var.
--  • places.push_sent_at: her yer için bildirim EN FAZLA BİR KEZ gider (send-push atomik işaretler).
--  • Mevcut yayındaki yerler "bildirildi" sayılır (eski yerler için toplu bildirim gitmez).
-- Tekrar çalıştırmak güvenlidir.
-- ════════════════════════════════════════════════════════════════════════════

-- 1) Eski tetikleyiciler
drop trigger if exists on_place_insert on public.places;
drop trigger if exists "notify-new-place" on public.places;

-- 2) Bildirim işareti
alter table public.places add column if not exists push_sent_at timestamptz;
update public.places set push_sent_at = coalesce(push_sent_at, created_at, now())
 where status = 'approved' and not coalesce(is_hidden, false) and push_sent_at is null;

-- 3) Yer koruma tetikleyicileri: push_sent_at'i sadece sistem/sunucu değiştirir
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
  new.push_sent_at := null;
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

-- 4) Yayına girince send-push'u çağır (pg_net, arka planda)
create or replace function public.cg_notify_place_published()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  v_anon text := 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im51ZWJxdHplaXJweXl4dG9wdGxwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk1NDI0NzgsImV4cCI6MjA5NTExODQ3OH0.Yw_8t-PVCDfFZPzV4F5jZjratLkAIE9X9sRdq2qme9Y';  -- herkese açık anon anahtar (uygulamada da var)
begin
  if new.status = 'approved' and not coalesce(new.is_hidden, false) and new.push_sent_at is null
     and (tg_op = 'INSERT' or old.status is distinct from 'approved' or coalesce(old.is_hidden, false)) then
    perform net.http_post(
      url     := 'https://nuebqtzeirpyyxtoptlp.supabase.co/functions/v1/send-push',
      body    := jsonb_build_object('placeId', new.id),
      params  := '{}'::jsonb,
      headers := jsonb_build_object('Content-Type', 'application/json', 'apikey', v_anon, 'Authorization', 'Bearer ' || v_anon),
      timeout_milliseconds := 10000
    );
  end if;
  return null;
end $$;
revoke all on function public.cg_notify_place_published() from public, anon, authenticated;

drop trigger if exists cg_notify_place_published on public.places;
create trigger cg_notify_place_published
  after insert or update of status, is_hidden on public.places
  for each row execute function public.cg_notify_place_published();
