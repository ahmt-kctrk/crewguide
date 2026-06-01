#!/usr/bin/env python3
# CrewGuide patch22.py — Admin Paneli
#   1. screen-admin HTML ekranı
#   2. Admin paneli CSS
#   3. loadAdminPlaces() + renderAdminPlaces() fonksiyonları
#   4. Settings ekranına "Admin Paneli" butonu (sadece admin görür)
#   5. goTo → screen-admin tetikleyicisi
#   6. Şehre göre filtre + arama

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: Admin paneli ekranı HTML ─────────────────────────────────────────
old1 = "</div>\n\n</div>\n\n<script>"

new1 = """</div>

  <!-- SCREEN: ADMIN PANELİ -->
  <div class="screen" id="screen-admin">
    <div class="status-bar">
      <span class="status-time">09:41</span>
      <div class="status-icons"><div class="status-icon signal"></div><div class="status-icon battery"></div></div>
    </div>
    <div class="navy-header">
      <div class="nav-back" onclick="goTo('screen-settings')">← </div>
      <div class="header-title font-display">Admin Paneli</div>
      <div class="header-sub" id="admin-panel-sub">Tüm yerler</div>
    </div>

    <!-- Arama + filtre -->
    <div style="padding:10px 16px;display:flex;gap:8px;flex-shrink:0;">
      <div style="position:relative;flex:1;">
        <input type="text" id="admin-search" placeholder="Yer veya kullanıcı ara..."
          style="width:100%;padding:9px 12px 9px 32px;border:1.5px solid var(--border);border-radius:var(--radius-sm);font-size:13px;font-family:'DM Sans',sans-serif;background:var(--white);outline:none;"
          oninput="filterAdminPlaces()">
        <span style="position:absolute;left:10px;top:50%;transform:translateY(-50%);font-size:14px;opacity:0.4;">🔍</span>
      </div>
      <select id="admin-city-filter" onchange="filterAdminPlaces()"
        style="padding:9px 10px;border:1.5px solid var(--border);border-radius:var(--radius-sm);font-size:12px;font-family:'DM Sans',sans-serif;background:var(--white);color:var(--text-primary);outline:none;cursor:pointer;">
        <option value="all">Tüm Şehirler</option>
      </select>
    </div>

    <!-- Stat bar -->
    <div style="display:flex;gap:0;padding:0 16px 10px;flex-shrink:0;">
      <div class="admin-stat-chip" id="admin-stat-total">— yer</div>
      <div class="admin-stat-chip" style="color:#10b981;" id="admin-stat-visible">— görünür</div>
      <div class="admin-stat-chip" style="color:#f59e0b;" id="admin-stat-hidden">— gizli</div>
    </div>

    <!-- Liste -->
    <div style="flex:1;overflow-y:auto;padding-bottom:20px;" id="admin-list">
      <div style="text-align:center;padding:40px;color:var(--text-muted);">⏳ Yükleniyor...</div>
    </div>
  </div>

</div>

<script>"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: screen-admin HTML eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI (</div></div><script>)")

# ── PATCH 2: Admin paneli CSS ──────────────────────────────────────────────────
old2 = "  .saved-filter-btn { flex-shrink:0;"
new2 = """  /* Admin paneli */
  .admin-stat-chip { font-size:11px; font-weight:600; color:var(--text-muted); padding:4px 10px 4px 0; }
  .admin-place-row { display:flex; align-items:flex-start; gap:10px; padding:12px 16px; border-bottom:1px solid var(--border); background:var(--white); }
  .admin-place-row:active { background:var(--cream-dark); }
  .admin-place-emoji { width:40px; height:40px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:20px; flex-shrink:0; }
  .admin-place-body { flex:1; min-width:0; }
  .admin-place-name { font-weight:600; font-size:13px; color:var(--text-primary); }
  .admin-place-meta { font-size:11px; color:var(--text-muted); margin-top:2px; line-height:1.5; }
  .admin-place-actions { display:flex; flex-direction:column; gap:5px; flex-shrink:0; }
  .admin-btn { padding:5px 10px; border-radius:8px; font-size:11px; font-family:'Syne',sans-serif; font-weight:600; border:none; cursor:pointer; white-space:nowrap; }
  .admin-btn-view  { background:#f0f3f9; color:var(--navy); }
  .admin-btn-hide  { background:#fef9ec; color:#92400e; border:1px solid #fde68a; }
  .admin-btn-show  { background:#f0fdf4; color:#166534; border:1px solid #bbf7d0; }
  .admin-btn-del   { background:#fef2f2; color:#ef4444; border:1px solid #fca5a5; }
  .admin-hidden-badge { display:inline-block; font-size:9px; padding:2px 6px; background:#fef9ec; color:#92400e; border-radius:4px; font-weight:600; margin-left:4px; vertical-align:middle; }
  .saved-filter-btn { flex-shrink:0;"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: Admin CSS eklendi")
else:
    patches.append("✗ Patch 2 BULUNAMADI (saved-filter-btn CSS)")

# ── PATCH 3: Admin fonksiyonları ──────────────────────────────────────────────
old3 = "async function adminDeletePlace() {"
new3 = """// ── ADMİN PANELİ ─────────────────────────────────────────────────────────────
let allAdminPlaces = [];
let adminFilteredPlaces = [];

async function loadAdminPlaces() {
  if (!isAdmin()) { showToast('Yetkisiz!'); goTo('screen-home'); return; }

  const listEl = document.getElementById('admin-list');
  if (listEl) listEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">⏳ Yükleniyor...</div>';

  try {
    const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;
    // is_hidden filtresi YOK — hem görünür hem gizli çek
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/places?order=created_at.desc&limit=300&select=id,name,emoji,city,cat,price,likes,rating,is_hidden,user_id,created_at,addr`,
      { headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token } }
    );
    if (!res.ok) throw new Error(await res.text());
    allAdminPlaces = await res.json();

    // Şehir filtresini doldur
    const cities = [...new Set(allAdminPlaces.map(p => p.city).filter(Boolean))].sort();
    const sel = document.getElementById('admin-city-filter');
    if (sel) {
      sel.innerHTML = '<option value="all">Tüm Şehirler</option>' +
        cities.map(c => `<option value="${c}">${c}</option>`).join('');
    }

    filterAdminPlaces();
  } catch(e) {
    console.error('[Admin] Yükleme hatası:', e);
    if (listEl) listEl.innerHTML = `<div style="text-align:center;padding:40px;color:#ef4444;">⚠️ Yüklenemedi: ${e.message}</div>`;
  }
}

function filterAdminPlaces() {
  const search = (document.getElementById('admin-search')?.value || '').toLowerCase().trim();
  const city   = document.getElementById('admin-city-filter')?.value || 'all';

  adminFilteredPlaces = allAdminPlaces.filter(p => {
    if (city !== 'all' && p.city !== city) return false;
    if (search) {
      const haystack = `${p.name} ${p.city} ${p.addr || ''}`.toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    return true;
  });

  renderAdminPlaces();
}

function renderAdminPlaces() {
  const listEl = document.getElementById('admin-list');
  if (!listEl) return;

  const total   = allAdminPlaces.length;
  const visible = allAdminPlaces.filter(p => !p.is_hidden).length;
  const hidden  = allAdminPlaces.filter(p =>  p.is_hidden).length;

  const totalEl   = document.getElementById('admin-stat-total');
  const visibleEl = document.getElementById('admin-stat-visible');
  const hiddenEl  = document.getElementById('admin-stat-hidden');
  if (totalEl)   totalEl.textContent   = `${total} yer`;
  if (visibleEl) visibleEl.textContent = `${visible} görünür`;
  if (hiddenEl)  hiddenEl.textContent  = `${hidden} gizli`;

  const subEl = document.getElementById('admin-panel-sub');
  if (subEl) subEl.textContent = adminFilteredPlaces.length !== total
    ? `${adminFilteredPlaces.length} / ${total} yer`
    : `${total} yer`;

  if (!adminFilteredPlaces.length) {
    listEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">Sonuç yok</div>';
    return;
  }

  const catBg = { food:'#fef3c7', shopping:'#e0e7ff', sightseeing:'#dcfce7' };

  listEl.innerHTML = adminFilteredPlaces.map(p => {
    const bg = catBg[p.cat] || '#f0f3f9';
    const date = new Date(p.created_at).toLocaleDateString('tr-TR', { day:'numeric', month:'short', year:'numeric' });
    const catLabel = p.cat==='food'?'Yemek':p.cat==='shopping'?'Alışveriş':'Gezi';
    const hiddenBadge = p.is_hidden ? '<span class="admin-hidden-badge">GİZLİ</span>' : '';

    return `
      <div class="admin-place-row">
        <div class="admin-place-emoji" style="background:${bg};">${p.emoji || '📍'}</div>
        <div class="admin-place-body">
          <div class="admin-place-name">${p.name} ${hiddenBadge}</div>
          <div class="admin-place-meta">
            📍 ${p.city || '—'} · ${catLabel} · ${p.price || '$'}<br>
            ♥ ${p.likes || 0} · ⭐ ${p.rating ? parseFloat(p.rating).toFixed(1) : '—'} · 📅 ${date}
          </div>
        </div>
        <div class="admin-place-actions">
          <button class="admin-btn admin-btn-view" onclick="adminViewPlace('${p.id}')">👁 Gör</button>
          ${p.is_hidden
            ? `<button class="admin-btn admin-btn-show" onclick="adminToggleHide('${p.id}', false, this)">✓ Göster</button>`
            : `<button class="admin-btn admin-btn-hide" onclick="adminToggleHide('${p.id}', true, this)">🚫 Gizle</button>`
          }
          <button class="admin-btn admin-btn-del" onclick="adminPermanentDelete('${p.id}', '${p.name.replace(/'/g, "\\'")}', this)">🗑 Sil</button>
        </div>
      </div>`;
  }).join('');
}

function adminViewPlace(placeId) {
  // places dizisinde varsa direkt aç, yoksa admin listesinden bul
  const existing = places.find(p => String(p.id) === String(placeId));
  if (existing) {
    openDetail(placeId);
    return;
  }
  // Admin listesinden al, geçici olarak places'e ekle
  const ap = allAdminPlaces.find(p => String(p.id) === String(placeId));
  if (!ap) return;
  const pn = { '$':{tr:'Uygun',en:'Budget'}, '$$':{tr:'Orta',en:'Mid-range'}, '$$$':{tr:'Pahalı',en:'Expensive'} };
  places.push({
    id: ap.id, cat: ap.cat, subcat: ap.subcat || '', emoji: ap.emoji || '📍',
    name: ap.name, addr: ap.addr || '', city: ap.city || '',
    price: ap.price || '$', priceName: pn[ap.price] || {tr:'Uygun',en:'Budget'},
    likes: ap.likes || 0, rating: parseFloat(ap.rating) || 0,
    ratingCount: ap.rating_count || 0, ratings: {5:0,4:0,3:0,2:0,1:0},
    userRating: 0, isAdult: false, userId: ap.user_id || null,
    desc: { tr: ap.desc_tr || '', en: ap.desc_en || '' }
  });
  openDetail(placeId);
}

async function adminToggleHide(placeId, hide, btn) {
  if (!isAdmin()) return;
  if (btn) { btn.disabled = true; btn.textContent = '⏳'; }

  try {
    const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;
    const res = await fetch(`${SUPABASE_URL}/rest/v1/places?id=eq.${placeId}`, {
      method: 'PATCH',
      headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'Prefer': 'return=minimal' },
      body: JSON.stringify({ is_hidden: hide })
    });
    if (!res.ok) throw new Error(await res.text());

    // Local güncelle
    const ap = allAdminPlaces.find(p => String(p.id) === String(placeId));
    if (ap) ap.is_hidden = hide;
    const lp = places.find(p => String(p.id) === String(placeId));
    if (lp && hide) {
      places.splice(places.indexOf(lp), 1);
      renderCards();
    }

    showToast(hide ? '🚫 Yer gizlendi.' : '✓ Yer gösterildi.');
    renderAdminPlaces();
  } catch(e) {
    console.error('[adminToggleHide]', e);
    showToast('Hata: ' + e.message);
    if (btn) { btn.disabled = false; btn.textContent = hide ? '🚫 Gizle' : '✓ Göster'; }
  }
}

async function adminPermanentDelete(placeId, placeName, btn) {
  if (!isAdmin()) return;
  const confirmed = confirm(`"${placeName}" yerini kalıcı olarak silmek istediğinden emin misin?\n\nBu işlem geri alınamaz.`);
  if (!confirmed) return;

  if (btn) { btn.disabled = true; btn.textContent = '⏳'; }

  try {
    const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;
    const res = await fetch(`${SUPABASE_URL}/rest/v1/places?id=eq.${placeId}`, {
      method: 'DELETE',
      headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token }
    });
    if (!res.ok) throw new Error(await res.text());

    allAdminPlaces = allAdminPlaces.filter(p => String(p.id) !== String(placeId));
    const lp = places.find(p => String(p.id) === String(placeId));
    if (lp) { places.splice(places.indexOf(lp), 1); renderCards(); }

    showToast(`🗑 "${placeName}" silindi.`);
    filterAdminPlaces();
  } catch(e) {
    console.error('[adminPermanentDelete]', e);
    showToast('Hata: ' + e.message);
    if (btn) { btn.disabled = false; btn.textContent = '🗑 Sil'; }
  }
}

async function adminDeletePlace() {"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: Admin panel fonksiyonları eklendi")
else:
    patches.append("✗ Patch 3 BULUNAMADI (adminDeletePlace)")

# ── PATCH 4: Settings ekranına Admin butonu ───────────────────────────────────
old4 = """      <button onclick="resetTheme()" style="width:100%;padding:14px;border-radius:var(--radius);border:1.5px solid var(--border);background:transparent;font-size:13px;color:var(--text-muted);cursor:pointer;font-family:'DM Sans',sans-serif;" id="btn-reset-theme">↺ Varsayılana Sıfırla</button>
      <button onclick="signOut()" style="width:100%;padding:14px;border-radius:var(--radius);border:1.5px solid #fca5a5;background:transparent;font-size:13px;color:#ef4444;cursor:pointer;font-family:'DM Sans',sans-serif;" id="btn-sign-out">🚪 Çıkış Yap</button>"""

new4 = """      <button onclick="resetTheme()" style="width:100%;padding:14px;border-radius:var(--radius);border:1.5px solid var(--border);background:transparent;font-size:13px;color:var(--text-muted);cursor:pointer;font-family:'DM Sans',sans-serif;" id="btn-reset-theme">↺ Varsayılana Sıfırla</button>
      <div id="admin-panel-btn-wrap" style="display:none;">
        <button onclick="goTo('screen-admin')" style="width:100%;padding:14px;border-radius:var(--radius);border:1.5px solid var(--navy);background:var(--navy);font-size:13px;color:#fff;cursor:pointer;font-family:'Syne',sans-serif;font-weight:600;">🛡 Admin Paneli</button>
      </div>
      <button onclick="signOut()" style="width:100%;padding:14px;border-radius:var(--radius);border:1.5px solid #fca5a5;background:transparent;font-size:13px;color:#ef4444;cursor:pointer;font-family:'DM Sans',sans-serif;" id="btn-sign-out">🚪 Çıkış Yap</button>"""

if old4 in html:
    html = html.replace(old4, new4)
    patches.append("✓ Patch 4: Settings ekranına Admin butonu eklendi")
else:
    patches.append("✗ Patch 4 BULUNAMADI (resetTheme / signOut butonları)")

# ── PATCH 5: goTo → screen-admin + settings admin butonu göster ───────────────
old5 = """  // Kayıtlı ekranı açılınca listeyi render et
  if (id === 'screen-saved') {
    renderSavedScreen();
  }"""

new5 = """  // Kayıtlı ekranı açılınca listeyi render et
  if (id === 'screen-saved') {
    renderSavedScreen();
  }

  // Admin paneli açılınca yükle
  if (id === 'screen-admin') {
    loadAdminPlaces();
  }

  // Settings açılınca admin butonunu göster/gizle
  if (id === 'screen-settings') {
    const adminWrap = document.getElementById('admin-panel-btn-wrap');
    if (adminWrap) adminWrap.style.display = isAdmin() ? 'block' : 'none';
  }"""

if old5 in html:
    html = html.replace(old5, new5)
    patches.append("✓ Patch 5: goTo screen-admin + settings admin butonu")
else:
    patches.append("✗ Patch 5 BULUNAMADI (screen-saved goTo)")

# ── SONUÇ ─────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("CrewGuide Patch 22 Sonuçları")
print("="*60)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup22', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    failed  = len([p for p in patches if p.startswith("✗")])
    print(f"\n✅ {applied} patch uygulandı!")
    if failed:
        print(f"⚠️  {failed} patch bulunamadı")
    print("📦 Yedek: index.html.backup22")
else:
    print("\n⚠ Değişiklik yapılmadı")
print("="*60 + "\n")
