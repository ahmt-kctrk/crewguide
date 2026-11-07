-- KURU ÇALIŞTIRMA: hiçbir şey kaydedilmez (bildirim de gitmez), sonunda sonuçları hata mesajı olarak gösterir.
do $outer$
declare res text;
begin
execute $mig$-- ════════════════════════════════════════════════════════════════════════════
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
$mig$;
execute $t$
create temp table _r(step text, ok text);
grant all on _r to public;
insert into _r select 'old triggers gone', (select (count(*)=0)::text from pg_trigger where tgrelid='public.places'::regclass and tgname in ('on_place_insert','notify-new-place'));
insert into _r select 'published without push_sent_at', (select count(*)::text from public.places where status='approved' and not coalesce(is_hidden,false) and push_sent_at is null);
insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at) values
 ('00000000-0000-0000-0000-000000000000','b1111111-0000-0000-0000-000000000001','authenticated','authenticated','pu1@example.invalid','{"username":"pu1","invited_by":"CRW-MASTER"}',now(),now());
create temp table _q0 as select coalesce(max(id),0) m from net.http_request_queue;
grant all on _q0 to public;
-- normal kullanıcı yer önerir → onay bekler → bildirim YOK
select set_config('request.jwt.claims', '{"sub":"b1111111-0000-0000-0000-000000000001","role":"authenticated"}', true);
set local role authenticated;
insert into public.places (id, cat, name, city, push_sent_at) values ('dryrun-push-1','food','Push Test','Seoul', now());
reset role;
insert into _r select 'pending insert → no push', (select count(*)::text from net.http_request_queue where id > (select m from _q0) and url like '%send-push%');
insert into _r select 'client cannot pre-set push_sent_at', (select (push_sent_at is null)::text from public.places where id='dryrun-push-1');
-- admin onaylar → 1 bildirim
update public.places set status='approved', is_hidden=false where id='dryrun-push-1';
insert into _r select 'approve → 1 push', (select count(*)::text from net.http_request_queue where id > (select m from _q0) and url like '%send-push%');
insert into _r select 'push body', (select convert_from(body,'utf8') from net.http_request_queue where id > (select m from _q0) and url like '%send-push%' order by id desc limit 1);
insert into _r select 'push has no service key', (select (not (headers::text ilike '%service_role%'))::text from net.http_request_queue where id > (select m from _q0) and url like '%send-push%' order by id desc limit 1);
-- başka bir alan güncellenirse tekrar bildirim YOK
update public.places set name='Push Test 2' where id='dryrun-push-1';
update public.places set is_hidden=false where id='dryrun-push-1';
insert into _r select 'later updates → still 1', (select count(*)::text from net.http_request_queue where id > (select m from _q0) and url like '%send-push%');
-- sahibi push_sent_at'i değiştiremez
update public.places set push_sent_at = now() where id='dryrun-push-1';
select set_config('request.jwt.claims', '{"sub":"b1111111-0000-0000-0000-000000000001","role":"authenticated"}', true);
set local role authenticated;
update public.places set push_sent_at = null where id='dryrun-push-1';
reset role;
insert into _r select 'owner cannot reset push_sent_at', (select (push_sent_at is not null)::text from public.places where id='dryrun-push-1');
$t$;
select string_agg(step||' = '||ok, E'\n') into res from _r;
raise exception 'DRYRUN RESULTS (rolled back):%', E'\n'||res;
end $outer$;
