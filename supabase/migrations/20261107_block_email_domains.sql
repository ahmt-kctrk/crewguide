-- ════════════════════════════════════════════════════════════════════════════
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
