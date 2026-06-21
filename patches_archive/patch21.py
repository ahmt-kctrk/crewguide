#!/usr/bin/env python3
# CrewGuide patch21.py - Kayıtlı yerler sistemi + kategoriye göre filtre

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: savedIds sistemi ─────────────────────────────────────────────────
old1 = "let liked = false;\nlet saved = false;"
new1 = """let liked = false;
let saved = false;

// ── KAYITLI YERLER ────────────────────────────────────────────────────────────
let savedIds = new Set(JSON.parse(localStorage.getItem('cg_saved_ids') || '[]'));

function persistSavedIds() {
  localStorage.setItem('cg_saved_ids', JSON.stringify([...savedIds]));
}

function isSaved(placeId) {
  return savedIds.has(String(placeId));
}

async function syncFavoritesFromSupabase() {
  if (!currentUser) return;
  try {
    const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/favorites?user_id=eq.${currentUser.id}&select=place_id`,
      { headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token } }
    );
    if (!res.ok) return;
    const rows = await res.json();
    rows.forEach(r => savedIds.add(String(r.place_id)));
    persistSavedIds();
  } catch(e) { console.warn('[Favorites] Sync hatasi:', e); }
}"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: savedIds sistemi eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── PATCH 2: toggleSave() gerçek mantık ──────────────────────────────────────
old2 = """function toggleSave() {
  saved = !saved;
  const btn = document.getElementById('detail-save-btn');
  const btn2 = document.getElementById('btn-save-detail');
  btn.textContent = saved ? '🔖' : '🔖';
  btn.style.background = saved ? '#fef3c7' : 'rgba(255,255,255,0.9)';
  document.getElementById('save-label').textContent = saved ? (lang==='tr'?'Kaydedildi':'Saved') : (lang==='tr'?'Kaydet':'Save');
  showToast(saved ? (lang==='tr'?'Kayıtlılara eklendi!':'Added to saved!') : (lang==='tr'?'Kaydedilenlerden çıkarıldı.':'Removed from saved.'));
}"""

new2 = """async function toggleSave() {
  const placeId = currentDetailId;
  if (!placeId) return;

  saved = !saved;
  updateSaveUI(saved);

  if (saved) { savedIds.add(String(placeId)); }
  else { savedIds.delete(String(placeId)); }
  persistSavedIds();

  showToast(saved
    ? (lang==='tr' ? '🔖 Kayıtlılara eklendi!' : '🔖 Added to saved!')
    : (lang==='tr' ? 'Kaydedilenlerden çıkarıldı.' : 'Removed from saved.'));

  if (currentUser) {
    const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;
    const headers = { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' };
    try {
      if (saved) {
        await fetch(`${SUPABASE_URL}/rest/v1/favorites`, {
          method: 'POST',
          headers: { ...headers, 'Prefer': 'resolution=ignore-duplicates,return=minimal' },
          body: JSON.stringify({ user_id: currentUser.id, place_id: placeId })
        });
      } else {
        await fetch(`${SUPABASE_URL}/rest/v1/favorites?user_id=eq.${currentUser.id}&place_id=eq.${placeId}`, {
          method: 'DELETE', headers
        });
      }
    } catch(e) { console.warn('[Favorites] Supabase hatasi:', e); }
  }
}

function updateSaveUI(isSavedState) {
  const btn = document.getElementById('detail-save-btn');
  const labelEl = document.getElementById('save-label');
  if (btn) {
    btn.style.background = isSavedState ? '#fef3c7' : 'rgba(255,255,255,0.9)';
    btn.style.borderColor = isSavedState ? 'var(--gold)' : '';
  }
  if (labelEl) labelEl.textContent = isSavedState
    ? (lang==='tr' ? 'Kaydedildi' : 'Saved')
    : (lang==='tr' ? 'Kaydet' : 'Save');
}"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: toggleSave() gercek mantik")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ── PATCH 3: openDetail() saved state ────────────────────────────────────────
old3 = "  loadComments(p.id);\n  setTimeout(prefillCommentUsername, 300);\n  loadPlacePhotos(p.id);"
new3 = """  saved = isSaved(p.id);
  updateSaveUI(saved);

  loadComments(p.id);
  setTimeout(prefillCommentUsername, 300);
  loadPlacePhotos(p.id);"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: openDetail() saved state")
else:
    patches.append("✗ Patch 3 BULUNAMADI")

# ── PATCH 4: screen-saved HTML ────────────────────────────────────────────────
old4 = """  <div class="screen" id="screen-saved">
    <div class="status-bar">
      <span class="status-time">09:41</span>
      <div class="status-icons"><div class="status-icon signal"></div><div class="status-icon battery"></div></div>
    </div>
    <div class="navy-header">
      <div class="nav-back" onclick="goTo('screen-home')" id="back-saved"></div>
      <div class="header-title font-display" id="saved-title">Kayıtlı Yerler</div>
      <div class="header-sub" id="saved-sub">Beğendiklerini kaydet</div>
    </div>
    <div style="flex:1;padding:20px;display:flex;flex-direction:column;gap:12px;" id="saved-content">
      <div style="text-align:center;padding:40px 20px;color:var(--text-muted);">
        <div style="font-size:40px;margin-bottom:12px;">🔖</div>
        <div style="font-size:14px;" id="saved-empty">Henüz kayıtlı yer yok. Beğendiğin yerleri kaydet!</div>
      </div>
    </div>"""

new4 = """  <div class="screen" id="screen-saved">
    <div class="status-bar">
      <span class="status-time">09:41</span>
      <div class="status-icons"><div class="status-icon signal"></div><div class="status-icon battery"></div></div>
    </div>
    <div class="navy-header">
      <div class="nav-back" onclick="goTo('screen-home')" id="back-saved"></div>
      <div class="header-title font-display" id="saved-title">Kayıtlı Yerler</div>
      <div class="header-sub" id="saved-sub">Beğendiklerini kaydet</div>
    </div>
    <div style="display:flex;gap:6px;padding:10px 16px;overflow-x:auto;flex-shrink:0;scrollbar-width:none;">
      <button class="saved-filter-btn active" onclick="setSavedFilter('all',this)" id="sf-all">Tümü</button>
      <button class="saved-filter-btn" onclick="setSavedFilter('food',this)" id="sf-food">🍜 Yemek</button>
      <button class="saved-filter-btn" onclick="setSavedFilter('shopping',this)" id="sf-shopping">🛍 Alışveriş</button>
      <button class="saved-filter-btn" onclick="setSavedFilter('sightseeing',this)" id="sf-sight">🗺 Gezi</button>
    </div>
    <div style="flex:1;overflow-y:auto;padding-bottom:80px;" id="saved-content">
      <div style="text-align:center;padding:40px 20px;color:var(--text-muted);">
        <div style="font-size:40px;margin-bottom:12px;">🔖</div>
        <div style="font-size:14px;" id="saved-empty">Henüz kayıtlı yer yok. Beğendiğin yerleri kaydet!</div>
      </div>
    </div>"""

if old4 in html:
    html = html.replace(old4, new4)
    patches.append("✓ Patch 4: screen-saved filtre butonlari HTML")
else:
    patches.append("✗ Patch 4 BULUNAMADI")

# ── PATCH 5: CSS ──────────────────────────────────────────────────────────────
old5 = "  .comment-actions {"
new5 = """  .saved-filter-btn { flex-shrink:0; padding:6px 14px; border-radius:20px; border:1.5px solid var(--border); background:var(--white); font-size:12px; font-family:'DM Sans',sans-serif; font-weight:500; color:var(--text-secondary); cursor:pointer; white-space:nowrap; transition:all 0.15s; }
  .saved-filter-btn.active { background:var(--navy); color:var(--white); border-color:var(--navy); font-weight:600; }
  .saved-place-card { display:flex; align-items:center; gap:12px; padding:12px 16px; border-bottom:1px solid var(--border); cursor:pointer; background:var(--white); transition:background 0.15s; }
  .saved-place-card:active { background:var(--cream-dark); }
  .saved-place-icon { width:44px; height:44px; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:22px; flex-shrink:0; }
  .saved-place-info { flex:1; min-width:0; }
  .saved-place-name { font-weight:600; font-size:14px; color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .saved-place-meta { font-size:11px; color:var(--text-muted); margin-top:2px; }
  .saved-place-right { display:flex; flex-direction:column; align-items:flex-end; gap:4px; flex-shrink:0; }
  .saved-place-rating { font-size:12px; color:#f59e0b; }
  .saved-remove-btn { background:none; border:none; font-size:15px; color:var(--text-muted); cursor:pointer; padding:2px 4px; }
  .comment-actions {"""

if old5 in html:
    html = html.replace(old5, new5)
    patches.append("✓ Patch 5: CSS eklendi")
else:
    patches.append("✗ Patch 5 BULUNAMADI")

# ── PATCH 6: renderSavedScreen + setSavedFilter fonksiyonları ─────────────────
old6 = "// ── PROFİL: EKLEDİĞİM YERLER ────────────────────────────────────────────────"
new6 = """// ── KAYITLI YERLER EKRANI ────────────────────────────────────────────────────
let activeSavedFilter = 'all';

function setSavedFilter(cat, el) {
  activeSavedFilter = cat;
  document.querySelectorAll('.saved-filter-btn').forEach(b => b.classList.remove('active'));
  if (el) el.classList.add('active');
  renderSavedScreen();
}

async function renderSavedScreen() {
  const content = document.getElementById('saved-content');
  if (!content) return;

  const lblMap = { 'sf-all': {tr:'Tümü',en:'All'}, 'sf-food': {tr:'🍜 Yemek',en:'🍜 Food'}, 'sf-shopping': {tr:'🛍 Alışveriş',en:'🛍 Shopping'}, 'sf-sight': {tr:'🗺 Gezi',en:'🗺 Sightseeing'} };
  Object.entries(lblMap).forEach(([id, lbl]) => { const el = document.getElementById(id); if (el) el.textContent = lbl[lang] || lbl.tr; });

  if (!savedIds.size) {
    content.innerHTML = `<div style="text-align:center;padding:60px 20px;color:var(--text-muted);"><div style="font-size:48px;margin-bottom:16px;">🔖</div><div style="font-size:14px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">${lang==='tr'?'Henüz kayıtlı yer yok':'No saved places yet'}</div><div style="font-size:13px;">${lang==='tr'?'Beğendiğin yerlerde 🔖 Kaydet\'e bas':'Tap 🔖 Save on places you like'}</div></div>`;
    return;
  }

  let savedPlaces = [...savedIds].map(id => places.find(p => String(p.id) === String(id))).filter(Boolean);

  const missingIds = [...savedIds].filter(id => !places.find(p => String(p.id) === String(id)));
  if (missingIds.length > 0) {
    try {
      const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;
      const ids = missingIds.join(',');
      const res = await fetch(
        `${SUPABASE_URL}/rest/v1/places?id=in.(${ids})&is_hidden=eq.false&select=id,name,emoji,city,cat,subcat,price,likes,rating,rating_count,desc_tr,desc_en,user_id,addr`,
        { headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token } }
      );
      if (res.ok) {
        const extra = await res.json();
        const pn = { '$':{tr:'Uygun',en:'Budget'}, '$$':{tr:'Orta',en:'Mid-range'}, '$$$':{tr:'Pahalı',en:'Expensive'} };
        extra.forEach(row => {
          const p = { id:row.id, cat:row.cat, subcat:row.subcat||'', emoji:row.emoji||'📍', name:row.name, addr:row.addr||'', price:row.price||'$', priceName:pn[row.price]||{tr:'Uygun',en:'Budget'}, likes:row.likes||0, rating:parseFloat(row.rating)||0, ratingCount:row.rating_count||0, ratings:{5:0,4:0,3:0,2:0,1:0}, userRating:0, isAdult:false, userId:row.user_id||null, desc:{tr:row.desc_tr||'',en:row.desc_en||''}, city:row.city||'' };
          if (!places.find(x => String(x.id) === String(p.id))) places.push(p);
          savedPlaces.push(p);
        });
      }
    } catch(e) { console.warn('[SavedScreen]', e); }
  }

  if (activeSavedFilter !== 'all') {
    savedPlaces = savedPlaces.filter(p => p.cat === activeSavedFilter);
  }

  if (!savedPlaces.length) {
    content.innerHTML = `<div style="text-align:center;padding:40px 20px;color:var(--text-muted);font-size:13px;">${lang==='tr'?'Bu kategoride kayıtlı yer yok':'No saved places in this category'}</div>`;
    return;
  }

  const catBg = { food:'#fef3c7', shopping:'#e0e7ff', sightseeing:'#dcfce7' };
  content.innerHTML = savedPlaces.map(p => {
    const bg = catBg[p.cat] || '#f0f3f9';
    const stars = p.rating > 0 ? '★'.repeat(Math.round(p.rating)) : '';
    const catLabel = p.cat==='food'?(lang==='tr'?'Yemek':'Food'):p.cat==='shopping'?(lang==='tr'?'Alışveriş':'Shopping'):(lang==='tr'?'Gezi':'Sightseeing');
    return `<div class="saved-place-card" onclick="openDetail('${p.id}')"><div class="saved-place-icon" style="background:${bg};">${p.emoji}</div><div class="saved-place-info"><div class="saved-place-name">${p.name}</div><div class="saved-place-meta">${p.city||''} · ${catLabel} · ${p.price}</div></div><div class="saved-place-right">${stars?`<div class="saved-place-rating">${stars}</div>`:''}<button class="saved-remove-btn" onclick="event.stopPropagation();removeSaved('${p.id}')" title="${lang==='tr'?'Kaldır':'Remove'}">🗑</button></div></div>`;
  }).join('');
}

async function removeSaved(placeId) {
  savedIds.delete(String(placeId));
  persistSavedIds();
  showToast(lang==='tr' ? 'Kaydedilenlerden çıkarıldı.' : 'Removed from saved.');
  renderSavedScreen();
  if (currentUser) {
    const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;
    try {
      await fetch(`${SUPABASE_URL}/rest/v1/favorites?user_id=eq.${currentUser.id}&place_id=eq.${placeId}`, {
        method: 'DELETE', headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + token }
      });
    } catch(e) { console.warn('[RemoveSaved]', e); }
  }
}

// ── PROFİL: EKLEDİĞİM YERLER ────────────────────────────────────────────────"""

if old6 in html:
    html = html.replace(old6, new6)
    patches.append("✓ Patch 6: renderSavedScreen + setSavedFilter + removeSaved")
else:
    patches.append("✗ Patch 6 BULUNAMADI")

# ── PATCH 7: goTo → screen-saved ─────────────────────────────────────────────
old7 = """  // Profil ekranı açılınca gerçek veriyi yükle
  if (id === 'screen-profile-view') {
    loadMyPlaces();
    renderProfileVisitedCities();
  }"""

new7 = """  // Profil ekranı açılınca gerçek veriyi yükle
  if (id === 'screen-profile-view') {
    loadMyPlaces();
    renderProfileVisitedCities();
  }

  // Kayıtlı ekranı açılınca listeyi render et
  if (id === 'screen-saved') {
    renderSavedScreen();
  }"""

if old7 in html:
    html = html.replace(old7, new7)
    patches.append("✓ Patch 7: goTo → screen-saved renderSavedScreen")
else:
    patches.append("✗ Patch 7 BULUNAMADI")

# ── PATCH 8: Giriş sonrası favorites sync ────────────────────────────────────
old8 = """  // Stat sayaçlarını sıfırla — loadMyPlaces dolduracak
  const spEl = document.getElementById('stat-places');
  const slEl = document.getElementById('stat-likes');
  if (spEl) spEl.textContent = '—';
  if (slEl) slEl.textContent = '—';"""

new8 = """  // Stat sayaçlarını sıfırla — loadMyPlaces dolduracak
  const spEl = document.getElementById('stat-places');
  const slEl = document.getElementById('stat-likes');
  if (spEl) spEl.textContent = '—';
  if (slEl) slEl.textContent = '—';

  // Supabase favorites sync
  setTimeout(syncFavoritesFromSupabase, 1500);"""

if old8 in html:
    html = html.replace(old8, new8)
    patches.append("✓ Patch 8: Giriş sonrası favorites sync")
else:
    patches.append("✗ Patch 8 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("CrewGuide Patch 21 Sonuçları")
print("="*60)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup21', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    failed  = len([p for p in patches if p.startswith("✗")])
    print(f"\n✅ {applied} patch uygulandı!")
    if failed:
        print(f"⚠️  {failed} patch bulunamadı")
    print("📦 Yedek: index.html.backup21")
else:
    print("\n⚠ Değişiklik yapılmadı")
print("="*60 + "\n")
