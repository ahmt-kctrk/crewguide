-- ════════════════════════════════════════════════════════════════════════════
-- CrewGuide — Bildirim dili + hesap silme hazırlığı
-- Supabase Dashboard → SQL Editor → tamamını yapıştır → Run  (tekrar çalıştırmak güvenli)
-- ════════════════════════════════════════════════════════════════════════════

-- 1) Bildirimler abonenin dilinde gitsin
alter table public.push_subscriptions add column if not exists lang text default 'tr';

-- 2) Kullanıcı kendi hesabını silince içerikleri isimsiz kalabilsin
--    (user_id boş bırakılabilir olmalı; kolon yoksa adım atlanır)
do $$
declare t text;
begin
  foreach t in array array['comments', 'ratings', 'places'] loop
    if exists (select 1 from information_schema.columns
               where table_schema = 'public' and table_name = t and column_name = 'user_id') then
      execute format('alter table public.%I alter column user_id drop not null', t);
    end if;
  end loop;
end $$;

-- Kontrol
select table_name, column_name, is_nullable
from information_schema.columns
where table_schema = 'public'
  and ((table_name = 'push_subscriptions' and column_name = 'lang')
    or (table_name in ('comments', 'ratings', 'places') and column_name = 'user_id'));
