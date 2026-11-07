-- KURU ÇALIŞTIRMA: hiçbir şey kaydedilmez, sonunda sonuçları hata mesajı olarak gösterir.
do $outer$
declare res text;
begin
execute $mig$-- ════════════════════════════════════════════════════════════════════════════
-- CrewGuide — Belirli e-posta alan adlarıyla kayıt engeli (7 Kasım 2026)
--  • @thy.com (ve alt alan adları, ör. @x.thy.com) ile yeni kayıt yapılamaz.
--  • Mevcut bir hesabın e-postası da bu alan adına değiştirilemez.
--  • Liste cg_email_blocked() içinde; istemcideki BLOCKED_EMAIL_DOMAINS ile aynı tutulmalı.
-- Tekrar çalıştırmak güvenlidir.
-- ════════════════════════════════════════════════════════════════════════════

create or replace function public.cg_email_blocked(p_email text)
returns boolean language sql immutable set search_path = '' as $$
  select exists (
    select 1
      from unnest(array['thy.com']) as b(domain),
           (select substring(lower(trim(coalesce(p_email, ''))) from '@([^@]+)$') as d) x
     where x.d = b.domain or x.d like '%.' || b.domain
  );
$$;

create or replace function public.cg_block_email_domains()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if tg_op = 'INSERT' then
    if public.cg_email_blocked(new.email) then
      raise exception 'EMAIL_DOMAIN_BLOCKED: bu alan adiyla kayit yapilamaz';
    end if;
  else
    if new.email is distinct from old.email and public.cg_email_blocked(new.email) then
      raise exception 'EMAIL_DOMAIN_BLOCKED: bu alan adina gecilemez';
    end if;
    if new.email_change is distinct from old.email_change and public.cg_email_blocked(new.email_change) then
      raise exception 'EMAIL_DOMAIN_BLOCKED: bu alan adina gecilemez';
    end if;
  end if;
  return new;
end $$;

revoke all on function public.cg_block_email_domains() from public, anon, authenticated;

drop trigger if exists cg_block_email_domains on auth.users;
create trigger cg_block_email_domains
  before insert or update of email, email_change on auth.users
  for each row execute function public.cg_block_email_domains();
$mig$;
execute $t$
create temp table _r(step text, ok text);
-- engellenmesi gerekenler
do $x$ declare e text; begin
  foreach e in array array['test@thy.com','Test@THY.COM','x@mail.thy.com','  y@thy.com '] loop
    begin
      insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at)
      values ('00000000-0000-0000-0000-000000000000', gen_random_uuid(), 'authenticated','authenticated', e,
              '{"username":"t","invited_by":"CRW-MASTER"}', now(), now());
      insert into _r values ('blocked '||e, 'NO (BUG)');
    exception when others then
      insert into _r values ('blocked '||e, case when sqlerrm like 'EMAIL_DOMAIN_BLOCKED%' then 'yes' else 'other error: '||left(sqlerrm,60) end);
    end;
  end loop;
end $x$;
-- izin verilmesi gerekenler
insert into auth.users (instance_id, id, aud, role, email, raw_user_meta_data, created_at, updated_at)
values ('00000000-0000-0000-0000-000000000000', '44444444-4444-4444-4444-444444444444', 'authenticated','authenticated','ok@gmail.com',
        '{"username":"t4","invited_by":"CRW-MASTER"}', now(), now());
insert into _r select 'gmail allowed', (select count(*)::text from public.profiles where id='44444444-4444-4444-4444-444444444444');
insert into _r select 'notthy.com allowed', (not public.cg_email_blocked('a@notthy.com'))::text;
insert into _r select 'thy.com.tr allowed', (not public.cg_email_blocked('a@thy.com.tr'))::text;
-- mevcut hesabın e-postası thy.com'a değiştirilemez
do $x$ begin
  update auth.users set email_change='ok@thy.com' where id='44444444-4444-4444-4444-444444444444';
  insert into _r values ('email_change blocked','NO (BUG)');
exception when others then insert into _r values ('email_change blocked', (sqlerrm like 'EMAIL_DOMAIN_BLOCKED%')::text); end $x$;
do $x$ begin
  update auth.users set email='ok@thy.com' where id='44444444-4444-4444-4444-444444444444';
  insert into _r values ('email update blocked','NO (BUG)');
exception when others then insert into _r values ('email update blocked', (sqlerrm like 'EMAIL_DOMAIN_BLOCKED%')::text); end $x$;
update auth.users set email='ok2@gmail.com' where id='44444444-4444-4444-4444-444444444444';
insert into _r select 'normal email update ok', (select email from auth.users where id='44444444-4444-4444-4444-444444444444');
update auth.users set raw_user_meta_data = raw_user_meta_data where id='44444444-4444-4444-4444-444444444444';
insert into _r values ('other updates ok','true');
$t$;
select string_agg(step||' = '||ok, E'\n') into res from _r;
raise exception 'DRYRUN RESULTS (rolled back):%', E'\n'||res;
end $outer$;
