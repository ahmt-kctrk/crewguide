#!/usr/bin/env python3
# CrewGuide patch17.py
# 1. Bildirimler ekranı (🔔) — son 20 yer, okundu işareti
# 2. Şehirler listesi dinamik — Supabase'den + popularCities birleşik
# 3. Ülkeye göre gruplu gösterim
# 4. Yer ekleme formuna ülke + şehir dropdown
# 5. submitPlace → country_tr, country_en, flag kaydet
# 6. Alt nav'a 🔔 ikonu ekle

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
# PATCH 1: Bildirimler ekranı HTML — screen-saved'den önce ekle
# ══════════════════════════════════════════════════════════════════════════════

old1 = """  <!-- SCREEN: SAVED -->
  <div class="screen" id="screen-saved">"""

new1 = """  <!-- SCREEN: NOTIFICATIONS -->
  <div class="screen" id="screen-notif">
    <div class="status-bar">
      <span class="status-time">09:41</span>
      <div class="status-icons"><div class="status-icon signal"></div><div class="status-icon battery"></div></div>
    </div>
    <div class="navy-header">
      <div class="nav-back" onclick="goTo('screen-home')">← </div>
      <div class="header-title font-display" id="notif-title">Bildirimler</div>
      <div class="header-sub" id="notif-sub">Son eklenen yerler</div>
    </div>
    <div style="flex:1;overflow-y:auto;padding:12px 16px 80px;">
      <div id="notif-list" style="display:flex;flex-direction:column;gap:8px;">
        <!-- JS tarafından doldurulur -->
      </div>
    </div>
    <div class="bottom-nav">
      <div class="bnav-item" onclick="goTo('screen-home')"><div class="bnav-icon">🏠</div><div class="bnav-label">Keşfet</div></div>
      <div class="bnav-item" onclick="goTo('screen-saved')"><div class="bnav-icon">🔖</div><div class="bnav-label">Kayıtlı</div></div>
      <div class="bnav-item" onclick="goTo('screen-add')"><div class="bnav-add">＋</div></div>
      <div class="bnav-item active"><div class="bnav-icon">🔔</div><div class="bnav-label">Bildirimler</div></div>
      <div class="bnav-item" onclick="goTo('screen-profile-view')"><div class="bnav-icon">👤</div><div class="bnav-label">Profil</div></div>
    </div>
  </div>

  <!-- SCREEN: SAVED -->
  <div class="screen" id="screen-saved">"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: Bildirimler ekranı HTML eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI (screen-saved)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 2: Alt nav'lara 🔔 ikonu ekle (home, saved, profile ekranları)
# ══════════════════════════════════════════════════════════════════════════════

old2a = """      <div class="bnav-item active"><div class="bnav-icon">🏠</div><div class="bnav-label" id="bnav-home">Keşfet</div></div>
      <div class="bnav-item" onclick="goTo('screen-saved')"><div class="bnav-icon">🔖</div><div class="bnav-label" id="bnav-saved">Kayıtlı</div></div>
      <div class="bnav-item" onclick="goTo('screen-add')"><div class="bnav-add">＋</div></div>
      <div class="bnav-item" onclick="goTo('screen-profile-view')"><div class="bnav-icon">👤</div><div class="bnav-label" id="bnav-profile">Profil</div></div>"""

new2a = """      <div class="bnav-item active"><div class="bnav-icon">🏠</div><div class="bnav-label" id="bnav-home">Keşfet</div></div>
      <div class="bnav-item" onclick="goTo('screen-saved')"><div class="bnav-icon">🔖</div><div class="bnav-label" id="bnav-saved">Kayıtlı</div></div>
      <div class="bnav-item" onclick="goTo('screen-add')"><div class="bnav-add">＋</div></div>
      <div class="bnav-item" onclick="openNotifScreen()" style="position:relative;"><div class="bnav-icon">🔔</div><div id="notif-badge" style="display:none;position:absolute;top:2px;right:calc(50% - 14px);background:#ef4444;color:#fff;border-radius:50%;width:16px;height:16px;font-size:10px;font-family:'Syne',sans-serif;font-weight:700;display:none;align-items:center;justify-content:center;">0</div><div class="bnav-label" id="bnav-notif">Bildirim</div></div>
      <div class="bnav-item" onclick="goTo('screen-profile-view')"><div class="bnav-icon">👤</div><div class="bnav-label" id="bnav-profile">Profil</div></div>"""

if old2a in html:
    html = html.replace(old2a, new2a)
    patches.append("✓ Patch 2a: Home ekranı alt nav'a 🔔 eklendi")
else:
    patches.append("✗ Patch 2a BULUNAMADI (home bnav)")

old2b = """      <div class="bnav-item" onclick="goTo('screen-home')"><div class="bnav-icon">🏠</div><div class="bnav-label" id="bnav-home-saved">Keşfet</div></div>
      <div class="bnav-item active"><div class="bnav-icon">🔖</div><div class="bnav-label" id="bnav-saved-saved">Kayıtlı</div></div>
      <div class="bnav-item" onclick="goTo('screen-add')"><div class="bnav-add">＋</div></div>
      <div class="bnav-item" onclick="goTo('screen-profile-view')"><div class="bnav-icon">👤</div><div class="bnav-label" id="bnav-profile-saved">Profil</div></div>"""

new2b = """      <div class="bnav-item" onclick="goTo('screen-home')"><div class="bnav-icon">🏠</div><div class="bnav-label" id="bnav-home-saved">Keşfet</div></div>
      <div class="bnav-item active"><div class="bnav-icon">🔖</div><div class="bnav-label" id="bnav-saved-saved">Kayıtlı</div></div>
      <div class="bnav-item" onclick="goTo('screen-add')"><div class="bnav-add">＋</div></div>
      <div class="bnav-item" onclick="openNotifScreen()"><div class="bnav-icon">🔔</div><div class="bnav-label">Bildirim</div></div>
      <div class="bnav-item" onclick="goTo('screen-profile-view')"><div class="bnav-icon">👤</div><div class="bnav-label" id="bnav-profile-saved">Profil</div></div>"""

if old2b in html:
    html = html.replace(old2b, new2b)
    patches.append("✓ Patch 2b: Saved ekranı alt nav'a 🔔 eklendi")
else:
    patches.append("✗ Patch 2b BULUNAMADI (saved bnav)")

old2c = """      <div class="bnav-item" onclick="goTo('screen-home')"><div class="bnav-icon">🏠</div><div class="bnav-label" id="bnav-home-profile">Keşfet</div></div>
      <div class="bnav-item" onclick="goTo('screen-saved')"><div class="bnav-icon">🔖</div><div class="bnav-label" id="bnav-saved-profile">Kayıtlı</div></div>
      <div class="bnav-item" onclick="goTo('screen-add')"><div class="bnav-add">＋</div></div>
      <div class="bnav-item active"><div class="bnav-icon">👤</div><div class="bnav-label" id="bnav-profile-profile">Profil</div></div>"""

new2c = """      <div class="bnav-item" onclick="goTo('screen-home')"><div class="bnav-icon">🏠</div><div class="bnav-label" id="bnav-home-profile">Keşfet</div></div>
      <div class="bnav-item" onclick="goTo('screen-saved')"><div class="bnav-icon">🔖</div><div class="bnav-label" id="bnav-saved-profile">Kayıtlı</div></div>
      <div class="bnav-item" onclick="goTo('screen-add')"><div class="bnav-add">＋</div></div>
      <div class="bnav-item" onclick="openNotifScreen()"><div class="bnav-icon">🔔</div><div class="bnav-label">Bildirim</div></div>
      <div class="bnav-item active"><div class="bnav-icon">👤</div><div class="bnav-label" id="bnav-profile-profile">Profil</div></div>"""

if old2c in html:
    html = html.replace(old2c, new2c)
    patches.append("✓ Patch 2c: Profile ekranı alt nav'a 🔔 eklendi")
else:
    patches.append("✗ Patch 2c BULUNAMADI (profile bnav)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 3: Yer ekleme formuna ülke + şehir dropdown ekle
# ══════════════════════════════════════════════════════════════════════════════

old3 = """      <div class="field-group">
        <div class="field-label" id="label-place-name">YER ADI</div>
        <input class="field-input" type="text" id="input-place-name" placeholder="Mukbang BBQ">
      </div>
      <div class="field-group">
        <div class="field-label" id="label-place-addr">ADRES / KONUM</div>"""

new3 = """      <!-- Ülke + Şehir Seçimi -->
      <div class="field-group" id="country-city-group">
        <div class="field-label" id="label-country-city">ÜLKE & ŞEHİR</div>
        <div style="display:flex;gap:8px;">
          <select id="select-country" onchange="onCountryChange()" style="
            flex:1;padding:11px 12px;background:var(--white);border:1.5px solid var(--border);
            border-radius:var(--radius-sm);font-size:13px;font-family:'DM Sans',sans-serif;
            color:var(--text-primary);outline:none;cursor:pointer;">
            <option value="">Ülke seç...</option>
          </select>
          <select id="select-city-add" onchange="onCityAddChange()" style="
            flex:1;padding:11px 12px;background:var(--white);border:1.5px solid var(--border);
            border-radius:var(--radius-sm);font-size:13px;font-family:'DM Sans',sans-serif;
            color:var(--text-primary);outline:none;cursor:pointer;">
            <option value="">Şehir seç...</option>
          </select>
        </div>
        <div id="selected-city-display" style="font-size:11px;color:var(--text-muted);margin-top:4px;"></div>
      </div>
      <div class="field-group">
        <div class="field-label" id="label-place-name">YER ADI</div>
        <input class="field-input" type="text" id="input-place-name" placeholder="Mukbang BBQ">
      </div>
      <div class="field-group">
        <div class="field-label" id="label-place-addr">ADRES / KONUM</div>"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: Yer ekleme formuna ülke+şehir dropdown eklendi")
else:
    patches.append("✗ Patch 3 BULUNAMADI (label-place-name)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 4: submitPlace → country_tr, country_en, flag kaydet
# ══════════════════════════════════════════════════════════════════════════════

old4 = """        city: currentCity || 'Seoul',
        price: priceVal,
        price_name_tr: (priceName[priceVal]||{}).tr || 'Uygun',"""

new4 = """        city: currentCity || 'Seoul',
        country_tr: currentCountry ? currentCountry.tr : '',
        country_en: currentCountry ? currentCountry.en : '',
        flag: currentFlag || '',
        price: priceVal,
        price_name_tr: (priceName[priceVal]||{}).tr || 'Uygun',"""

if old4 in html:
    html = html.replace(old4, new4)
    patches.append("✓ Patch 4: submitPlace → country/flag kaydediliyor")
else:
    patches.append("✗ Patch 4 BULUNAMADI (submitPlace city)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 5: filterCities → Supabase'den dinamik şehirler + popularCities birleşik
# ══════════════════════════════════════════════════════════════════════════════

old5 = """function filterCities(q) {
  const list = document.getElementById('city-list');
  const query = q.trim().toLowerCase();
  const filtered = query
    ? popularCities.filter(c => c.name.toLowerCase().includes(query) || c.country[lang].toLowerCase().includes(query))
    : popularCities;

  let html = '';
  // Current location button at top
  html += `<div onclick="useCurrentLocation()" style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;background:var(--cream);cursor:pointer;margin-bottom:4px;border:1px solid var(--border);">
    <span style="font-size:16px;">📍</span>
    <div style="display:flex;align-items:baseline;gap:6px;">
      <div style="font-size:13px;font-weight:500;color:var(--navy);">${lang==='tr'?'Mevcut Konumum':'My Current Location'}</div>
      <div style="font-size:11px;color:var(--text-muted);">${lang==='tr'?'GPS ile algıla':'Detect via GPS'}</div>
    </div>
  </div>`;

  filtered.forEach(c => {
    html += `<div onclick="selectCity('${c.name}','${c.country[lang]}','${c.flag}')" style="display:flex;align-items:center;gap:8px;padding:7px 10px;border-radius:8px;cursor:pointer;transition:background 0.15s;" onmouseover="this.style.background='var(--cream)'" onmouseout="this.style.background=''">
      <span style="font-size:18px;flex-shrink:0;">${c.flag}</span>
      <div style="display:flex;align-items:baseline;gap:6px;">
        <div style="font-size:13px;font-weight:500;color:var(--text-primary);">${c.name}</div>
        <div style="font-size:11px;color:var(--text-muted);">${c.country[lang]}</div>
      </div>
    </div>`;
  });

  if (filtered.length === 0 && query) {
    html += `<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:13px;">${lang==='tr'?'Şehir bulunamadı':'City not found'}</div>`;
  }
  list.innerHTML = html;
}"""

new5 = """// Supabase'den çekilen dinamik şehirler
let dynamicCities = [];

async function loadDynamicCities() {
  try {
    const res = await fetch(
      SUPABASE_URL + '/rest/v1/places?is_hidden=eq.false&select=city,country_tr,country_en,flag&order=city.asc',
      { headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + SUPABASE_KEY } }
    );
    const rows = await res.json();
    if (!Array.isArray(rows)) return;

    // Unique şehirler
    const seen = new Set();
    dynamicCities = [];
    rows.forEach(r => {
      if (!r.city || seen.has(r.city)) return;
      seen.add(r.city);
      // popularCities'de varsa onun country bilgisini kullan
      const pop = popularCities.find(p => p.name.toLowerCase() === r.city.toLowerCase());
      dynamicCities.push({
        name: r.city,
        country: pop ? pop.country : { tr: r.country_tr || r.city, en: r.country_en || r.city },
        flag: pop ? pop.flag : (r.flag || '🌍')
      });
    });
  } catch(e) {
    console.warn('[loadDynamicCities]', e);
  }
}

function getMergedCities() {
  // popularCities + dynamicCities — duplicate city'leri birleştir
  const merged = [...popularCities];
  dynamicCities.forEach(dc => {
    if (!merged.find(p => p.name.toLowerCase() === dc.name.toLowerCase())) {
      merged.push(dc);
    }
  });
  return merged.sort((a, b) => a.name.localeCompare(b.name));
}

function filterCities(q) {
  const list = document.getElementById('city-list');
  const query = q.trim().toLowerCase();
  const allCities = getMergedCities();
  const filtered = query
    ? allCities.filter(c => c.name.toLowerCase().includes(query) || c.country[lang]?.toLowerCase().includes(query))
    : allCities;

  let html = '';
  // Current location button at top
  html += `<div onclick="useCurrentLocation()" style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;background:var(--cream);cursor:pointer;margin-bottom:4px;border:1px solid var(--border);">
    <span style="font-size:16px;">📍</span>
    <div style="display:flex;align-items:baseline;gap:6px;">
      <div style="font-size:13px;font-weight:500;color:var(--navy);">${lang==='tr'?'Mevcut Konumum':'My Current Location'}</div>
      <div style="font-size:11px;color:var(--text-muted);">${lang==='tr'?'GPS ile algıla':'Detect via GPS'}</div>
    </div>
  </div>`;

  if (!query) {
    // Ülkeye göre gruplu göster
    const byCountry = {};
    filtered.forEach(c => {
      const countryName = c.country[lang] || c.country.en || '';
      if (!byCountry[countryName]) byCountry[countryName] = { flag: c.flag, cities: [] };
      byCountry[countryName].cities.push(c);
    });

    Object.keys(byCountry).sort().forEach(countryName => {
      const group = byCountry[countryName];
      html += `<div style="margin-top:8px;margin-bottom:2px;padding:4px 4px;font-size:11px;font-family:'Syne',sans-serif;font-weight:700;color:var(--text-muted);letter-spacing:0.05em;display:flex;align-items:center;gap:6px;">
        <span>${group.flag}</span> ${countryName.toUpperCase()}
      </div>`;
      group.cities.forEach(c => {
        html += `<div onclick="selectCity('${c.name}','${(c.country[lang]||'').replace(/'/g,"\\'")}','${c.flag}')" style="display:flex;align-items:center;gap:8px;padding:7px 10px 7px 22px;border-radius:8px;cursor:pointer;transition:background 0.15s;" onmouseover="this.style.background='var(--cream)'" onmouseout="this.style.background=''">
          <div style="font-size:13px;font-weight:500;color:var(--text-primary);">${c.name}</div>
        </div>`;
      });
    });
  } else {
    filtered.forEach(c => {
      html += `<div onclick="selectCity('${c.name}','${(c.country[lang]||'').replace(/'/g,"\\'")}','${c.flag}')" style="display:flex;align-items:center;gap:8px;padding:7px 10px;border-radius:8px;cursor:pointer;transition:background 0.15s;" onmouseover="this.style.background='var(--cream)'" onmouseout="this.style.background=''">
        <span style="font-size:18px;flex-shrink:0;">${c.flag}</span>
        <div style="display:flex;align-items:baseline;gap:6px;">
          <div style="font-size:13px;font-weight:500;color:var(--text-primary);">${c.name}</div>
          <div style="font-size:11px;color:var(--text-muted);">${c.country[lang]||''}</div>
        </div>
      </div>`;
    });
  }

  if (filtered.length === 0 && query) {
    html += `<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:13px;">${lang==='tr'?'Şehir bulunamadı':'City not found'}</div>`;
  }
  list.innerHTML = html;
}"""

if old5 in html:
    html = html.replace(old5, new5)
    patches.append("✓ Patch 5: filterCities → dinamik + gruplu gösterim")
else:
    patches.append("✗ Patch 5 BULUNAMADI (filterCities)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 6: openCityModal → loadDynamicCities çağır
# ══════════════════════════════════════════════════════════════════════════════

old6 = """function openCityModal() {
  document.getElementById('city-modal-title').textContent = lang==='tr' ? 'Şehir Seç' : 'Select City';
  document.getElementById('city-modal-sub').textContent = lang==='tr' ? 'Mevcut konumun veya başka bir şehir ara' : 'Use current location or search a city';
  document.getElementById('city-search-input').value = '';
  document.getElementById('city-search-input').placeholder = lang==='tr' ? 'Şehir ara...' : 'Search city...';
  filterCities('');
  goTo('screen-city');
}"""

new6 = """function openCityModal() {
  document.getElementById('city-modal-title').textContent = lang==='tr' ? 'Şehir Seç' : 'Select City';
  document.getElementById('city-modal-sub').textContent = lang==='tr' ? 'Mevcut konumun veya başka bir şehir ara' : 'Use current location or search a city';
  document.getElementById('city-search-input').value = '';
  document.getElementById('city-search-input').placeholder = lang==='tr' ? 'Şehir ara...' : 'Search city...';
  // Dinamik şehirleri yükle, sonra filtrele
  loadDynamicCities().then(() => filterCities(''));
  goTo('screen-city');
}"""

if old6 in html:
    html = html.replace(old6, new6)
    patches.append("✓ Patch 6: openCityModal → loadDynamicCities çağırıyor")
else:
    patches.append("✗ Patch 6 BULUNAMADI (openCityModal)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 7: Bildirimler JS — openNotifScreen, loadNotifs, renderNotifs
# ══════════════════════════════════════════════════════════════════════════════

old7 = """// ── DAVET KODLARI UI ──────────────────────────────────────────────────────────
function updateInviteCodesUI() {"""

new7 = """// ── BİLDİRİMLER ──────────────────────────────────────────────────────────────
let notifReadIds = JSON.parse(localStorage.getItem('notif_read_ids') || '[]');

async function openNotifScreen() {
  goTo('screen-notif');
  await loadNotifs();
}

async function loadNotifs() {
  const list = document.getElementById('notif-list');
  if (!list) return;
  list.innerHTML = `<div style="text-align:center;padding:40px;color:var(--text-muted);font-size:13px;">Yükleniyor...</div>`;

  try {
    const res = await fetch(
      SUPABASE_URL + '/rest/v1/places?is_hidden=eq.false&select=id,name,emoji,city,country_tr,country_en,flag,cat,created_at&order=created_at.desc&limit=20',
      { headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + SUPABASE_KEY } }
    );
    const places = await res.json();
    if (!Array.isArray(places) || places.length === 0) {
      list.innerHTML = `<div style="text-align:center;padding:40px;color:var(--text-muted);font-size:13px;">${lang==='tr'?'Henüz yer eklenmemiş':'No places added yet'}</div>`;
      return;
    }

    renderNotifs(places);

    // Okunmamış badge güncelle
    updateNotifBadge(places);

  } catch(e) {
    list.innerHTML = `<div style="text-align:center;padding:40px;color:var(--text-muted);font-size:13px;">Yüklenemedi</div>`;
    console.warn('[loadNotifs]', e);
  }
}

function renderNotifs(items) {
  const list = document.getElementById('notif-list');
  if (!list) return;

  list.innerHTML = items.map(p => {
    const isRead = notifReadIds.includes(p.id);
    const timeAgo = getTimeAgo(p.created_at);
    const country = lang==='tr' ? (p.country_tr||p.city||'') : (p.country_en||p.city||'');
    const flag = p.flag || '🌍';

    return `<div onclick="markNotifRead('${p.id}'); openNotifPlace('${p.id}')" style="
      display:flex;align-items:center;gap:12px;
      padding:12px 14px;border-radius:12px;
      background:${isRead ? 'var(--white)' : 'rgba(201,168,76,0.08)'};
      border:1px solid ${isRead ? 'var(--border)' : 'rgba(201,168,76,0.3)'};
      cursor:pointer;transition:background 0.2s;
      position:relative;">
      <div style="font-size:28px;flex-shrink:0;">${p.emoji||'📍'}</div>
      <div style="flex:1;min-width:0;">
        <div style="font-size:13px;font-weight:600;color:var(--text-primary);font-family:'Syne',sans-serif;">${p.name||''}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${flag} ${p.city||''} · ${country}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:1px;">${timeAgo}</div>
      </div>
      ${!isRead ? `<div style="width:8px;height:8px;border-radius:50%;background:var(--gold);flex-shrink:0;"></div>` : ''}
    </div>`;
  }).join('');
}

function markNotifRead(id) {
  if (!notifReadIds.includes(id)) {
    notifReadIds.push(id);
    localStorage.setItem('notif_read_ids', JSON.stringify(notifReadIds));
  }
  updateNotifBadge();
}

function markAllNotifsRead(items) {
  if (items) {
    items.forEach(p => {
      if (!notifReadIds.includes(p.id)) notifReadIds.push(p.id);
    });
    localStorage.setItem('notif_read_ids', JSON.stringify(notifReadIds));
  }
  updateNotifBadge();
}

function updateNotifBadge(items) {
  const badge = document.getElementById('notif-badge');
  if (!badge) return;
  if (items) {
    const unread = items.filter(p => !notifReadIds.includes(p.id)).length;
    if (unread > 0) {
      badge.style.display = 'flex';
      badge.textContent = unread > 9 ? '9+' : String(unread);
    } else {
      badge.style.display = 'none';
    }
  } else {
    badge.style.display = 'none';
  }
}

function openNotifPlace(placeId) {
  const p = places.find(x => x.id === placeId);
  if (p) {
    openDetail(p);
  } else {
    // places listesinde yoksa home'a dön
    goTo('screen-home');
  }
}

function getTimeAgo(isoDate) {
  if (!isoDate) return '';
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (lang === 'tr') {
    if (mins < 1) return 'Az önce';
    if (mins < 60) return `${mins} dakika önce`;
    if (hours < 24) return `${hours} saat önce`;
    if (days < 7) return `${days} gün önce`;
    return new Date(isoDate).toLocaleDateString('tr-TR');
  } else {
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return new Date(isoDate).toLocaleDateString('en-US');
  }
}

// ── ÜLKE/ŞEHİR DROPDOWN (Yer Ekleme) ─────────────────────────────────────────
let currentCountry = null;
let currentFlag = '';

// Ülke listesi — popularCities'den türetilir
function buildCountryOptions() {
  const select = document.getElementById('select-country');
  if (!select) return;

  const allCities = getMergedCities();
  const countries = {};
  allCities.forEach(c => {
    const key = c.country.en || c.name;
    if (!countries[key]) {
      countries[key] = { tr: c.country.tr, en: c.country.en, flag: c.flag, cities: [] };
    }
    countries[key].cities.push(c.name);
  });

  const sorted = Object.keys(countries).sort((a, b) => {
    const aName = lang==='tr' ? countries[a].tr : countries[a].en;
    const bName = lang==='tr' ? countries[b].tr : countries[b].en;
    return aName.localeCompare(bName);
  });

  select.innerHTML = `<option value="">${lang==='tr'?'Ülke seç...':'Select country...'}</option>`;
  sorted.forEach(key => {
    const c = countries[key];
    const name = lang==='tr' ? c.tr : c.en;
    const opt = document.createElement('option');
    opt.value = key;
    opt.textContent = `${c.flag} ${name}`;
    opt.dataset.tr = c.tr;
    opt.dataset.en = c.en;
    opt.dataset.flag = c.flag;
    opt.dataset.cities = JSON.stringify(c.cities);
    select.appendChild(opt);
  });

  // Mevcut şehri seç
  if (currentCity) {
    const match = allCities.find(c => c.name === currentCity);
    if (match) {
      const countryEn = match.country.en;
      select.value = countryEn;
      onCountryChange();
    }
  }
}

function onCountryChange() {
  const select = document.getElementById('select-country');
  const citySelect = document.getElementById('select-city-add');
  if (!select || !citySelect) return;

  const opt = select.options[select.selectedIndex];
  if (!opt || !opt.value) {
    currentCountry = null;
    currentFlag = '';
    citySelect.innerHTML = `<option value="">${lang==='tr'?'Şehir seç...':'Select city...'}</option>`;
    return;
  }

  currentCountry = { tr: opt.dataset.tr, en: opt.dataset.en };
  currentFlag = opt.dataset.flag;

  const cities = JSON.parse(opt.dataset.cities || '[]');
  citySelect.innerHTML = `<option value="">${lang==='tr'?'Şehir seç...':'Select city...'}</option>`;
  cities.sort().forEach(city => {
    const o = document.createElement('option');
    o.value = city;
    o.textContent = city;
    citySelect.appendChild(o);
  });

  // Mevcut şehri seç
  if (cities.includes(currentCity)) {
    citySelect.value = currentCity;
    onCityAddChange();
  }
}

function onCityAddChange() {
  const citySelect = document.getElementById('select-city-add');
  if (!citySelect) return;
  const city = citySelect.value;
  if (city) {
    currentCity = city;
    const display = document.getElementById('selected-city-display');
    if (display) display.textContent = `${currentFlag} ${city} · ${currentCountry?.[lang]||''}`;
  }
}

// ── DAVET KODLARI UI ──────────────────────────────────────────────────────────
function updateInviteCodesUI() {"""

if old7 in html:
    html = html.replace(old7, new7)
    patches.append("✓ Patch 7: Bildirimler JS + ülke/şehir dropdown JS eklendi")
else:
    patches.append("✗ Patch 7 BULUNAMADI (updateInviteCodesUI)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 8: screen-add açılınca country dropdown'ı doldur
# ══════════════════════════════════════════════════════════════════════════════

old8 = """  if (id === 'screen-add') {
    document.getElementById('add-sub').textContent = currentCity + ' · ' + (lang==='tr'?'Deneyimini paylaş':'Share your experience');"""

new8 = """  if (id === 'screen-add') {
    document.getElementById('add-sub').textContent = currentCity + ' · ' + (lang==='tr'?'Deneyimini paylaş':'Share your experience');
    // Ülke dropdown'ı doldur
    setTimeout(() => buildCountryOptions(), 100);"""

if old8 in html:
    html = html.replace(old8, new8)
    patches.append("✓ Patch 8: screen-add açılınca ülke dropdown dolduruluyor")
else:
    patches.append("✗ Patch 8 BULUNAMADI (screen-add)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 9: Home açılınca notif badge yükle
# ══════════════════════════════════════════════════════════════════════════════

old9 = """    if (currentUser && !realtimeConnected) {
      setTimeout(startRealtimeNotifications, 2000);
    }"""

new9 = """    if (currentUser && !realtimeConnected) {
      setTimeout(startRealtimeNotifications, 2000);
    }
    // Okunmamış bildirim sayısını güncelle
    setTimeout(async () => {
      try {
        const res = await fetch(
          SUPABASE_URL + '/rest/v1/places?is_hidden=eq.false&select=id&order=created_at.desc&limit=20',
          { headers: { 'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + SUPABASE_KEY } }
        );
        const items = await res.json();
        if (Array.isArray(items)) updateNotifBadge(items);
      } catch(e) {}
    }, 1000);"""

if old9 in html:
    html = html.replace(old9, new9)
    patches.append("✓ Patch 9: Home açılınca notif badge güncelleniyor")
else:
    patches.append("✗ Patch 9 BULUNAMADI (startRealtimeNotifications)")

# ══════════════════════════════════════════════════════════════════════════════
# SONUÇ
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("CrewGuide Patch 17 Sonuçları")
print("="*60)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup17', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    failed  = len([p for p in patches if p.startswith("✗")])
    print(f"\n✅ {applied} patch uygulandı!")
    if failed:
        print(f"⚠️  {failed} patch bulunamadı")
    print("📦 Yedek: index.html.backup17")
else:
    print("\n⚠ Değişiklik yapılmadı")
print("="*60 + "\n")

print("""
📋 SUPABASE SQL (places tablosuna kolonlar):
─────────────────────────────────────────────────────────
-- Zaten çalıştırdınız:
-- ALTER TABLE places ADD COLUMN IF NOT EXISTS country_tr text DEFAULT '';
-- ALTER TABLE places ADD COLUMN IF NOT EXISTS country_en text DEFAULT '';
-- ALTER TABLE places ADD COLUMN IF NOT EXISTS flag text DEFAULT '';
─────────────────────────────────────────────────────────
""")
