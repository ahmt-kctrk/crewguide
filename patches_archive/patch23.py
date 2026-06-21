#!/usr/bin/env python3
# CrewGuide patch23.py — Davet Kodu Yönetimi
#   1. Admin paneline "Davet Kodları" sekmesi
#   2. Tüm kullanıcıları + davet kodlarını listele
#   3. Kullanıcıya ek kod verme butonu
#   4. Davet ağacı görünümü (kim kimi davet etmiş)

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: Admin paneline sekme bar ekle ────────────────────────────────────
old1 = """    <!-- Arama + filtre -->
    <div style="padding:10px 16px;display:flex;gap:8px;flex-shrink:0;">"""

new1 = """    <!-- Sekme bar -->
    <div style="display:flex;border-bottom:2px solid var(--border);flex-shrink:0;background:var(--white);">
      <button class="admin-tab active" id="admin-tab-places" onclick="switchAdminTab('places')">📍 Yerler</button>
      <button class="admin-tab" id="admin-tab-invites" onclick="switchAdminTab('invites')">🎫 Davetler</button>
    </div>

    <!-- Yerler paneli -->
    <div id="admin-panel-places">
    <!-- Arama + filtre -->
    <div style="padding:10px 16px;display:flex;gap:8px;flex-shrink:0;">"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: Admin sekme bar eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── PATCH 2: Yerler panelini kapat, davetler panelini ekle ───────────────────
old2 = """    <!-- Liste -->
    <div style="flex:1;overflow-y:auto;padding-bottom:20px;" id="admin-list">
      <div style="text-align:center;padding:40px;color:var(--text-muted);">⏳ Yükleniyor...</div>
    </div>
  </div>"""

new2 = """    <!-- Liste -->
    <div style="flex:1;overflow-y:auto;padding-bottom:20px;" id="admin-list">
      <div style="text-align:center;padding:40px;color:var(--text-muted);">⏳ Yükleniyor...</div>
    </div>
    </div><!-- /admin-panel-places -->

    <!-- Davetler paneli -->
    <div id="admin-panel-invites" style="display:none;flex:1;overflow-y:auto;padding-bottom:20px;">
      <!-- Özet stat -->
      <div style="display:flex;gap:0;padding:10px 16px;flex-shrink:0;border-bottom:1px solid var(--border);background:var(--white);">
        <div class="admin-stat-chip" id="inv-stat-users">— kullanıcı</div>
        <div class="admin-stat-chip" style="color:#10b981;" id="inv-stat-used">— kullanıldı</div>
        <div class="admin-stat-chip" style="color:#f59e0b;" id="inv-stat-free">— boş</div>
      </div>
      <!-- Arama -->
      <div style="padding:10px 16px;">
        <div style="position:relative;">
          <input type="text" id="invite-admin-search" placeholder="Kullanıcı veya kod ara..."
            style="width:100%;padding:9px 12px 9px 32px;border:1.5px solid var(--border);border-radius:var(--radius-sm);font-size:13px;font-family:'DM Sans',sans-serif;background:var(--white);outline:none;"
            oninput="filterAdminInvites()">
          <span style="position:absolute;left:10px;top:50%;transform:translateY(-50%);font-size:14px;opacity:0.4;">🔍</span>
        </div>
      </div>
      <div id="admin-invites-list">
        <div style="text-align:center;padding:40px;color:var(--text-muted);">⏳ Yükleniyor...</div>
      </div>
    </div>
  </div>"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: Davetler paneli HTML eklendi")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ── PATCH 3: Admin sekme CSS ──────────────────────────────────────────────────
old3 = "  /* Admin paneli */"
new3 = """  /* Admin sekmeleri */
  .admin-tab { flex:1; padding:11px 0; border:none; background:none; font-size:13px; font-family:'DM Sans',sans-serif; font-weight:500; color:var(--text-muted); cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-2px; transition:all 0.15s; }
  .admin-tab.active { color:var(--navy); font-weight:700; border-bottom-color:var(--navy); }
  .invite-user-row { padding:12px 16px; border-bottom:1px solid var(--border); background:var(--white); }
  .invite-user-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }
  .invite-user-name { font-weight:600; font-size:13px; color:var(--text-primary); }
  .invite-user-meta { font-size:11px; color:var(--text-muted); }
  .invite-code-row { display:flex; align-items:center; gap:8px; padding:4px 0; }
  .invite-code-pill { font-family:'Syne',sans-serif; font-size:12px; font-weight:700; letter-spacing:1px; padding:3px 8px; border-radius:6px; }
  .invite-code-pill.used { background:#f0f3f9; color:var(--text-muted); text-decoration:line-through; }
  .invite-code-pill.free { background:#fef3c7; color:#92400e; }
  .invite-add-btn { font-size:11px; background:var(--navy); color:#fff; border:none; border-radius:6px; padding:4px 10px; cursor:pointer; font-family:'Syne',sans-serif; font-weight:600; }
  /* Admin paneli */"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: Admin sekme CSS eklendi")
else:
    patches.append("✗ Patch 3 BULUNAMADI")

# ── PATCH 4: switchAdminTab + loadAdminInvites + filterAdminInvites fonksiyonları
old4 = "// ── ADMİN PANELİ ─────────────────────────────────────────────────────────────"
new4 = """// ── ADMİN SEKME YÖNETİMİ ────────────────────────────────────────────────────
function switchAdminTab(tab) {
  document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('admin-tab-' + tab)?.classList.add('active');
  document.getElementById('admin-panel-places').style.display = tab === 'places' ? 'flex' : 'none';
  document.getElementById('admin-panel-places').style.flexDirection = 'column';
  document.getElementById('admin-panel-invites').style.display = tab === 'invites' ? 'block' : 'none';
  if (tab === 'invites' && !allAdminUsers.length) loadAdminInvites();
}

// ── ADMİN DAVET YÖNETİMİ ─────────────────────────────────────────────────────
let allAdminUsers = [];
let filteredAdminUsers = [];

async function loadAdminInvites() {
  if (!isAdmin()) return;
  const listEl = document.getElementById('admin-invites-list');
  if (listEl) listEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">⏳ Yükleniyor...</div>';

  try {
    const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;

    // Tüm profilleri çek
    const profRes = await fetch(
      `${SUPABASE_URL}/rest/v1/profiles?order=created_at.desc&select=id,username,invite_code,invited_by,created_at,role`,
      { headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token } }
    );
    if (!profRes.ok) throw new Error(await profRes.text());
    const profiles = await profRes.json();

    // Tüm davet kodlarını çek
    const invRes = await fetch(
      `${SUPABASE_URL}/rest/v1/invite_codes?order=created_at.asc&select=code,created_by,used_by,used_at`,
      { headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token } }
    );
    if (!invRes.ok) throw new Error(await invRes.text());
    const inviteCodes = await invRes.json();

    // Her profile'a kodlarını eşleştir
    allAdminUsers = profiles.map(p => ({
      ...p,
      codes: inviteCodes.filter(c => c.created_by === p.id)
    }));

    // İstatistikler
    const totalCodes = inviteCodes.length;
    const usedCodes  = inviteCodes.filter(c => c.used_by).length;
    const freeCodes  = totalCodes - usedCodes;
    document.getElementById('inv-stat-users').textContent  = `${profiles.length} kullanıcı`;
    document.getElementById('inv-stat-used').textContent   = `${usedCodes} kullanıldı`;
    document.getElementById('inv-stat-free').textContent   = `${freeCodes} boş`;

    filteredAdminUsers = [...allAdminUsers];
    renderAdminInvites();

  } catch(e) {
    console.error('[loadAdminInvites]', e);
    if (listEl) listEl.innerHTML = `<div style="text-align:center;padding:40px;color:#ef4444;">⚠️ ${e.message}</div>`;
  }
}

function filterAdminInvites() {
  const q = (document.getElementById('invite-admin-search')?.value || '').toLowerCase().trim();
  if (!q) {
    filteredAdminUsers = [...allAdminUsers];
  } else {
    filteredAdminUsers = allAdminUsers.filter(u =>
      u.username?.toLowerCase().includes(q) ||
      u.invite_code?.toLowerCase().includes(q) ||
      u.codes.some(c => c.code.toLowerCase().includes(q))
    );
  }
  renderAdminInvites();
}

function renderAdminInvites() {
  const listEl = document.getElementById('admin-invites-list');
  if (!listEl) return;

  if (!filteredAdminUsers.length) {
    listEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">Sonuç yok</div>';
    return;
  }

  listEl.innerHTML = filteredAdminUsers.map(u => {
    const joined = u.created_at ? new Date(u.created_at).toLocaleDateString('tr-TR', {day:'numeric',month:'short',year:'numeric'}) : '—';
    const usedCount = u.codes.filter(c => c.used_by).length;
    const freeCount = u.codes.filter(c => !c.used_by).length;
    const invitedByUser = u.invited_by ? allAdminUsers.find(x => x.invite_code === u.invited_by) : null;

    const codesHtml = u.codes.length
      ? u.codes.map(c => `
          <div class="invite-code-row">
            <span class="invite-code-pill ${c.used_by ? 'used' : 'free'}">${c.code}</span>
            <span style="font-size:10px;color:var(--text-muted);">
              ${c.used_by ? '✓ Kullanıldı' : '⬜ Boş'}
            </span>
            ${!c.used_by ? `<button onclick="copyInviteCode('${c.code}')" style="font-size:10px;background:none;border:1px solid var(--border);border-radius:4px;padding:2px 6px;cursor:pointer;color:var(--navy);">Kopyala</button>` : ''}
          </div>`).join('')
      : '<div style="font-size:11px;color:var(--text-muted);padding:4px 0;">Kodu yok</div>';

    return `
      <div class="invite-user-row">
        <div class="invite-user-header">
          <div>
            <div class="invite-user-name">
              ${u.username || 'İsimsiz'}
              ${u.role === 'admin' ? '<span style="font-size:10px;background:var(--navy);color:#fff;padding:1px 6px;border-radius:4px;margin-left:4px;">ADMIN</span>' : ''}
            </div>
            <div class="invite-user-meta">
              Katıldı: ${joined}
              ${invitedByUser ? ` · Davet eden: <b>${invitedByUser.username}</b>` : ' · (Kurucu/Master)'}
              · ${usedCount}/${u.codes.length} kullanıldı
            </div>
          </div>
          <button class="invite-add-btn" onclick="adminAddInviteCode('${u.id}', '${(u.username||'').replace(/'/g,"\\'")}')">+ Kod Ver</button>
        </div>
        <div style="padding-left:4px;">${codesHtml}</div>
      </div>`;
  }).join('');
}

async function adminAddInviteCode(userId, username) {
  if (!isAdmin()) return;
  const confirmed = confirm(`"${username}" kullanıcısına yeni davet kodu eklensin mi?`);
  if (!confirmed) return;

  const newCode = 'CRW-' + Math.random().toString(36).substring(2,5).toUpperCase() + Math.random().toString(36).substring(2,4).toUpperCase();

  try {
    await sbFetch('invite_codes', {
      method: 'POST',
      prefer: 'return=minimal',
      body: JSON.stringify({ code: newCode, created_by: userId })
    });
    showToast(`✓ "${newCode}" kodu eklendi!`);
    // Listeyi yenile
    allAdminUsers = [];
    await loadAdminInvites();
  } catch(e) {
    console.error('[adminAddInviteCode]', e);
    showToast('Hata: ' + e.message);
  }
}

// ── ADMİN PANELİ ─────────────────────────────────────────────────────────────"""

if old4 in html:
    html = html.replace(old4, new4)
    patches.append("✓ Patch 4: Davet yönetim fonksiyonları eklendi")
else:
    patches.append("✗ Patch 4 BULUNAMADI")

# ── PATCH 5: loadAdminPlaces çağrısında ilk sekmeyi göster ───────────────────
old5 = """async function loadAdminPlaces() {
  if (!isAdmin()) { showToast('Yetkisiz!'); goTo('screen-home'); return; }

  const listEl = document.getElementById('admin-list');
  if (listEl) listEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">⏳ Yükleniyor...</div>';"""

new5 = """async function loadAdminPlaces() {
  if (!isAdmin()) { showToast('Yetkisiz!'); goTo('screen-home'); return; }

  // İlk açılışta Yerler sekmesini göster
  const placesPanel = document.getElementById('admin-panel-places');
  const invitesPanel = document.getElementById('admin-panel-invites');
  if (placesPanel) { placesPanel.style.display = 'flex'; placesPanel.style.flexDirection = 'column'; }
  if (invitesPanel) invitesPanel.style.display = 'none';
  document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('admin-tab-places')?.classList.add('active');

  const listEl = document.getElementById('admin-list');
  if (listEl) listEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">⏳ Yükleniyor...</div>';"""

if old5 in html:
    html = html.replace(old5, new5)
    patches.append("✓ Patch 5: loadAdminPlaces sekme başlangıcı")
else:
    patches.append("✗ Patch 5 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("CrewGuide Patch 23 Sonuçları")
print("="*60)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup23', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    failed  = len([p for p in patches if p.startswith("✗")])
    print(f"\n✅ {applied} patch uygulandı!")
    if failed:
        print(f"⚠️  {failed} patch bulunamadı")
    print("📦 Yedek: index.html.backup23")
else:
    print("\n⚠ Değişiklik yapılmadı")
print("="*60 + "\n")
