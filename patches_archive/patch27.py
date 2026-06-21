#!/usr/bin/env python3
# CrewGuide patch27.py — Kullanıcı silme + devre dışı bırakma
# Admin: kullanıcı sil | Kullanıcı: hesabı devre dışı bırak
# Kullanım: python patch27.py

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 1 — CSS: Devre dışı kullanıcı stili + silme butonu
# ══════════════════════════════════════════════════════════════════════════════
old1 = "  .invite-add-btn { font-size:11px; background:var(--navy); color:#fff; border:none; border-radius:6px; padding:4px 10px; cursor:pointer; font-family:'Syne',sans-serif; font-weight:600; }"
new1 = """  .invite-add-btn { font-size:11px; background:var(--navy); color:#fff; border:none; border-radius:6px; padding:4px 10px; cursor:pointer; font-family:'Syne',sans-serif; font-weight:600; }
  .invite-delete-btn { font-size:11px; background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; border-radius:6px; padding:4px 10px; cursor:pointer; font-family:'Syne',sans-serif; font-weight:600; margin-left:4px; }
  .invite-user-row.disabled { opacity:0.5; }
  .disabled-badge { font-size:10px; background:#fee2e2; color:#991b1b; padding:1px 6px; border-radius:4px; margin-left:4px; }"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: CSS eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 2 — renderAdminInvites: Sil butonu + devre dışı badge
# ══════════════════════════════════════════════════════════════════════════════
old2 = """          <button class="invite-add-btn" onclick="adminAddInviteCode('${u.id}', '${(u.username||'').replace(/'/g,"\'")}')">+ Kod Ver</button>"""
new2 = """          <div style="display:flex;gap:4px;align-items:center;">
            <button class="invite-add-btn" onclick="adminAddInviteCode('${u.id}', '${(u.username||'').replace(/'/g,"\\'")}')">+ Kod Ver</button>
            ${u.is_disabled
              ? `<button class="invite-delete-btn" onclick="adminEnableUser('${u.id}','${(u.username||'').replace(/'/g,"\\'")}')">✓ Aktif Et</button>`
              : `<button class="invite-delete-btn" onclick="adminDeleteUser('${u.id}','${(u.username||'').replace(/'/g,"\\'")}')">🗑 Sil</button>`
            }
          </div>"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: Sil butonu eklendi")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 3 — renderAdminInvites: disabled badge username yanına
# ══════════════════════════════════════════════════════════════════════════════
old3 = """              ${u.username || 'İsimsiz'}
              ${u.role === 'admin' ? '<span style="font-size:10px;background:var(--navy);color:#fff;padding:1px 6px;border-radius:4px;margin-left:4px;">ADMIN</span>' : ''}"""
new3 = """              ${u.username || 'İsimsiz'}
              ${u.role === 'admin' ? '<span style="font-size:10px;background:var(--navy);color:#fff;padding:1px 6px;border-radius:4px;margin-left:4px;">ADMIN</span>' : ''}
              ${u.is_disabled ? '<span class="disabled-badge">Devre Dışı</span>' : ''}"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: Disabled badge eklendi")
else:
    patches.append("✗ Patch 3 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 4 — loadAdminInvites: is_disabled alanını çek
# ══════════════════════════════════════════════════════════════════════════════
old4 = "      `${SUPABASE_URL}/rest/v1/profiles?order=created_at.desc&select=id,username,invite_code,invited_by,created_at,role`,"
new4 = "      `${SUPABASE_URL}/rest/v1/profiles?order=created_at.desc&select=id,username,invite_code,invited_by,created_at,role,is_disabled`,"

if old4 in html:
    html = html.replace(old4, new4)
    patches.append("✓ Patch 4: is_disabled alanı sorguya eklendi")
else:
    patches.append("✗ Patch 4 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 5 — adminDeleteUser + adminEnableUser + disableAccount fonksiyonları
# adminAddInviteCode fonksiyonunun hemen altına
# ══════════════════════════════════════════════════════════════════════════════
old5 = "// ── ADMİN PANELİ ─────────────────────────────────────────────────────────────"
new5 = """// ── KULLANICI YÖNETİMİ ──────────────────────────────────────────────────────

async function manageUserAction(action, targetUserId) {
  const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token');
  const res = await fetch(`${SUPABASE_URL}/functions/v1/manage-user`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token,
      'apikey': SUPABASE_KEY,
    },
    body: JSON.stringify({ action, targetUserId })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'İşlem başarısız');
  return data;
}

async function adminDeleteUser(userId, username) {
  if (!isAdmin()) return;
  const confirmed = confirm(`"${username}" kullanıcısı kalıcı olarak silinecek!\n\nEklediği yerler gizlenecek, davet kodları silinecek.\n\nDevam etmek istiyor musun?`);
  if (!confirmed) return;

  try {
    showToast(lang === 'tr' ? '⏳ Siliniyor...' : '⏳ Deleting...');
    await manageUserAction('delete', userId);
    showToast(`✓ "${username}" silindi`);
    allAdminUsers = [];
    await loadAdminInvites();
  } catch(e) {
    console.error('[adminDeleteUser]', e);
    showToast('Hata: ' + e.message);
  }
}

async function adminEnableUser(userId, username) {
  if (!isAdmin()) return;
  const confirmed = confirm(`"${username}" hesabı yeniden aktif edilsin mi?`);
  if (!confirmed) return;

  try {
    await manageUserAction('enable', userId);
    showToast(`✓ "${username}" aktif edildi`);
    allAdminUsers = [];
    await loadAdminInvites();
  } catch(e) {
    console.error('[adminEnableUser]', e);
    showToast('Hata: ' + e.message);
  }
}

// Kullanıcı kendi hesabını devre dışı bırakır
async function disableMyAccount() {
  const confirmed = confirm(
    lang === 'tr'
      ? 'Hesabın devre dışı bırakılacak. Tekrar giriş yapamayacaksın.\nDevam etmek istiyor musun?'
      : 'Your account will be disabled. You will not be able to sign in again.\nContinue?'
  );
  if (!confirmed) return;

  try {
    await manageUserAction('disable', currentUser.id);
    showToast(lang === 'tr' ? 'Hesabın devre dışı bırakıldı.' : 'Account disabled.');
    // Çıkış yap
    sessionStorage.clear();
    localStorage.removeItem('sb_access_token');
    localStorage.removeItem('sb_refresh_token');
    localStorage.removeItem('sb_user');
    currentUser = null;
    currentProfile = null;
    setTimeout(() => goTo('screen-home'), 1500);
  } catch(e) {
    console.error('[disableMyAccount]', e);
    showToast('Hata: ' + e.message);
  }
}

// ── ADMİN PANELİ ─────────────────────────────────────────────────────────────"""

if "// ── ADMİN PANELİ ─────────────────────────────────────────────────────────────" in html:
    html = html.replace(
        "// ── ADMİN PANELİ ─────────────────────────────────────────────────────────────",
        new5
    )
    patches.append("✓ Patch 5: adminDeleteUser + adminEnableUser + disableMyAccount eklendi")
else:
    patches.append("✗ Patch 5 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 6 — Profil ekranına "Hesabımı Devre Dışı Bırak" butonu
# Çıkış yap butonunun hemen üstüne
# ══════════════════════════════════════════════════════════════════════════════
old6 = """          <button class="btn-outline" onclick="signOut()" style="width:100%;margin-top:8px;">"""
new6 = """          <button class="btn-outline" onclick="disableMyAccount()" style="width:100%;margin-top:8px;border-color:#fca5a5;color:#991b1b;">
            ⚠️ <span data-i18n="disable_account">Hesabımı Devre Dışı Bırak</span>
          </button>
          <button class="btn-outline" onclick="signOut()" style="width:100%;margin-top:8px;">"""

if old6 in html:
    html = html.replace(old6, new6)
    patches.append("✓ Patch 6: Profil ekranına devre dışı butonu eklendi")
else:
    patches.append("✗ Patch 6 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# Kaydet
# ══════════════════════════════════════════════════════════════════════════════
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*58}")
    print("CrewGuide patch27 — Kullanıcı silme + devre dışı")
    print('='*58)
    for p in patches:
        print(f"  {p}")
    print(f"""
── Supabase adımları ────────────────────────────────────
  1. SQL Editör:
     ALTER TABLE profiles
       ADD COLUMN IF NOT EXISTS is_disabled BOOLEAN DEFAULT FALSE,
       ADD COLUMN IF NOT EXISTS disabled_at TIMESTAMPTZ;

  2. Edge Functions → New Function → "manage-user"
     manage-user/index.ts içeriğini yapıştır → Deploy

  3. manage-user fonksiyonu otomatik olarak
     SUPABASE_SERVICE_ROLE_KEY'i görür (default secret)

  4. python deploy.py "patch27: kullanıcı silme + devre dışı"
{'='*58}
""")
else:
    print("\n⚠️  Değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
