#!/usr/bin/env python3
# CrewGuide patch22.py — Çalışma saati + "Şu an açık" badge
# Google Places API entegrasyonu (Text Search → Place Details)
# Uygulama: python patch22.py

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
# PATCH 1 — CSS: Hours badge stilleri
# map-placeholder'ın hemen üstüne oturur
# ══════════════════════════════════════════════════════════════════════════════
old1 = "  .map-placeholder { width: 100%; height: 80px; background: #e8f4f0; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; font-size: 13px; color: #2d6a4f; margin-bottom: 16px; gap: 6px; border: 1px solid #b7e4c7; cursor: pointer; }"
new1 = """  .map-placeholder { width: 100%; height: 80px; background: #e8f4f0; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; font-size: 13px; color: #2d6a4f; margin-bottom: 16px; gap: 6px; border: 1px solid #b7e4c7; cursor: pointer; }

  /* ── ÇALIŞMA SAATİ BADGE ── */
  .hours-badge {
    display: flex; align-items: center; gap: 8px;
    padding: 10px 14px; border-radius: var(--radius-sm);
    margin-bottom: 12px; font-size: 13px;
    border: 1px solid; cursor: default;
    transition: opacity 0.2s;
  }
  .hours-badge.open {
    background: #f0fdf4; border-color: #86efac; color: #166534;
  }
  .hours-badge.closed {
    background: #fef2f2; border-color: #fca5a5; color: #991b1b;
  }
  .hours-badge.unknown {
    background: #f8fafc; border-color: var(--border); color: var(--text-muted);
  }
  .hours-badge.loading {
    background: #fefce8; border-color: #fde047; color: #854d0e;
    animation: pulse-soft 1.5s infinite;
  }
  @keyframes pulse-soft {
    0%,100% { opacity:1; } 50% { opacity:0.6; }
  }
  .hours-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  }
  .hours-badge.open .hours-dot { background: #22c55e; }
  .hours-badge.closed .hours-dot { background: #ef4444; }
  .hours-badge.unknown .hours-dot { background: #9ca3af; }
  .hours-badge.loading .hours-dot { background: #eab308; }
  .hours-main { font-weight: 600; }
  .hours-detail { color: inherit; opacity: 0.75; font-size: 12px; }
  .hours-toggle {
    margin-left: auto; font-size: 11px; opacity: 0.6;
    background: none; border: none; cursor: pointer; color: inherit;
    padding: 2px 6px; border-radius: 4px;
    transition: background 0.15s;
  }
  .hours-toggle:hover { background: rgba(0,0,0,0.06); }
  .hours-week {
    display: none; flex-direction: column; gap: 3px;
    padding: 8px 14px 10px; border-radius: 0 0 var(--radius-sm) var(--radius-sm);
    background: #f8fafc; border: 1px solid var(--border); border-top: none;
    font-size: 12px; margin-top: -12px; margin-bottom: 12px;
  }
  .hours-week.visible { display: flex; }
  .hours-week-row { display: flex; justify-content: space-between; color: var(--text-secondary); }
  .hours-week-row.today { color: var(--text-primary); font-weight: 600; }"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: CSS hours badge eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI — CSS satırı değişmiş olabilir")


# ══════════════════════════════════════════════════════════════════════════════
# PATCH 2 — HTML: Detay sayfasına hours-badge ve hours-week div'leri ekle
# map-placeholder'ın hemen üstüne
# ══════════════════════════════════════════════════════════════════════════════
old2 = '      <div class="map-placeholder" id="map-placeholder-btn" onclick="openMapModal()">🗺 <span id="map-text">Haritada Göster</span></div>'
new2 = """      <!-- Çalışma saati badge -->
      <div class="hours-badge unknown" id="hours-badge" style="display:none;">
        <div class="hours-dot"></div>
        <span class="hours-main" id="hours-main">—</span>
        <span class="hours-detail" id="hours-detail"></span>
        <button class="hours-toggle" id="hours-toggle" onclick="toggleWeeklyHours()" style="display:none;">▾ Tümü</button>
      </div>
      <div class="hours-week" id="hours-week"></div>

      <div class="map-placeholder" id="map-placeholder-btn" onclick="openMapModal()">🗺 <span id="map-text">Haritada Göster</span></div>"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: HTML hours-badge eklendi")
else:
    patches.append("✗ Patch 2 BULUNAMADI")


# ══════════════════════════════════════════════════════════════════════════════
# PATCH 3 — JS: Google Places API anahtarı ve hours cache
# SUPABASE sabitleri bloğunun hemen altına
# ══════════════════════════════════════════════════════════════════════════════
old3 = "const SUPABASE_URL = 'https://nuebqtzeirpyyxtoptlp.supabase.co';"
new3 = """const SUPABASE_URL = 'https://nuebqtzeirpyyxtoptlp.supabase.co';

// ── GOOGLE PLACES API ────────────────────────────────────────────────────────
// Kendi API anahtarınızı buraya girin (Places API + Maps JavaScript API aktif olmalı)
// https://console.cloud.google.com → APIs & Services → Places API (New) etkinleştir
const GOOGLE_PLACES_KEY = '';  // ← Buraya API key girin

// Çalışma saati cache: place_id → { fetched_at, is_open, badge_text, detail_text, weekly }
const hoursCache = {};"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: GOOGLE_PLACES_KEY ve hoursCache eklendi")
else:
    patches.append("✗ Patch 3 BULUNAMADI")


# ══════════════════════════════════════════════════════════════════════════════
# PATCH 4 — JS: openDetail içine fetchPlaceHours çağrısı
# loadComments çağrısının hemen arkasına
# ══════════════════════════════════════════════════════════════════════════════
old4 = """  loadComments(p.id);
  setTimeout(prefillCommentUsername, 300);
  loadPlacePhotos(p.id);"""
new4 = """  loadComments(p.id);
  setTimeout(prefillCommentUsername, 300);
  loadPlacePhotos(p.id);
  fetchPlaceHours(p);  // çalışma saati badge"""

if old4 in html:
    html = html.replace(old4, new4)
    patches.append("✓ Patch 4: openDetail'e fetchPlaceHours çağrısı eklendi")
else:
    patches.append("✗ Patch 4 BULUNAMADI")


# ══════════════════════════════════════════════════════════════════════════════
# PATCH 5 — JS: loadPlaces'te opening_hours alanını map'le
# ══════════════════════════════════════════════════════════════════════════════
old5 = """        isAdult: row.is_adult || false,
        userId: row.user_id || null,
        desc: { tr: row.desc_tr || '', en: row.desc_en || '' }"""
new5 = """        isAdult: row.is_adult || false,
        userId: row.user_id || null,
        desc: { tr: row.desc_tr || '', en: row.desc_en || '' },
        googlePlaceId: row.google_place_id || null,
        openingHours: row.opening_hours || null"""

if old5 in html:
    html = html.replace(old5, new5)
    patches.append("✓ Patch 5: loadPlaces'e googlePlaceId + openingHours eklendi")
else:
    patches.append("✗ Patch 5 BULUNAMADI")


# ══════════════════════════════════════════════════════════════════════════════
# PATCH 6 — JS: fetchPlaceHours + renderHoursBadge + toggleWeeklyHours
# closeMapModal fonksiyonunun hemen üstüne ekle
# ══════════════════════════════════════════════════════════════════════════════
old6 = "async function openMapModal() {"
new6 = """// ── ÇALIŞMA SAATİ ────────────────────────────────────────────────────────────

const HOURS_TTL = 6 * 60 * 60 * 1000; // 6 saat cache

// Günün adları (Pazar=0)
const DAY_NAMES = {
  tr: ['Pazar','Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi'],
  en: ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
  de: ['Sonntag','Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag'],
  fr: ['Dimanche','Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'],
  es: ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'],
};

function getDayNames() {
  return DAY_NAMES[lang] || DAY_NAMES.en;
}

async function fetchPlaceHours(p) {
  const badge = document.getElementById('hours-badge');
  const weekEl = document.getElementById('hours-week');
  if (!badge) return;

  // Badge'i gizle, week panelini kapat
  badge.style.display = 'none';
  if (weekEl) { weekEl.classList.remove('visible'); weekEl.innerHTML = ''; }

  // 1) Önce cache'e bak
  const cacheKey = p.googlePlaceId || p.id;
  const cached = hoursCache[cacheKey];
  if (cached && Date.now() - cached.fetchedAt < HOURS_TTL) {
    renderHoursBadge(cached);
    return;
  }

  // 2) Supabase'de kayıtlı opening_hours var mı?
  if (p.openingHours) {
    const parsed = parseStoredHours(p.openingHours, p.googlePlaceId || p.id);
    hoursCache[cacheKey] = parsed;
    renderHoursBadge(parsed);
    // Arka planda taze çek (6 saat geçmişse)
    if (!cached) fetchFromGoogle(p);
    return;
  }

  // 3) API key yoksa sessizce çık
  if (!GOOGLE_PLACES_KEY) return;

  // 4) Google'dan çek
  fetchFromGoogle(p);
}

async function fetchFromGoogle(p) {
  const badge = document.getElementById('hours-badge');
  if (!badge) return;

  // Loading göster
  badge.className = 'hours-badge loading';
  badge.style.display = 'flex';
  document.getElementById('hours-main').textContent = lang === 'tr' ? 'Saatler yükleniyor...' : 'Loading hours...';
  document.getElementById('hours-detail').textContent = '';
  const toggleBtn = document.getElementById('hours-toggle');
  if (toggleBtn) toggleBtn.style.display = 'none';

  try {
    // Step 1: Text Search ile place_id bul (zaten yoksa)
    let placeId = p.googlePlaceId;
    if (!placeId) {
      const searchQuery = encodeURIComponent(`${p.name} ${p.addr}`);
      const searchRes = await fetch(
        `https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input=${searchQuery}&inputtype=textquery&fields=place_id&key=${GOOGLE_PLACES_KEY}`,
        { mode: 'cors' }
      );
      const searchData = await searchRes.json();
      if (searchData.candidates && searchData.candidates[0]) {
        placeId = searchData.candidates[0].place_id;
        // Supabase'e kaydet
        saveGooglePlaceId(p.id, placeId);
        p.googlePlaceId = placeId;
      }
    }

    if (!placeId) {
      badge.style.display = 'none';
      return;
    }

    // Step 2: Place Details ile opening_hours çek
    const detailRes = await fetch(
      `https://maps.googleapis.com/maps/api/place/details/json?place_id=${placeId}&fields=opening_hours,utc_offset_minutes&key=${GOOGLE_PLACES_KEY}`,
      { mode: 'cors' }
    );
    const detailData = await detailRes.json();
    const oh = detailData.result?.opening_hours;

    if (!oh) {
      badge.style.display = 'none';
      return;
    }

    // Supabase'e kaydet
    saveOpeningHours(p.id, placeId, oh);
    p.openingHours = oh;

    const cacheKey = placeId || p.id;
    const result = parseGoogleHours(oh, cacheKey);
    hoursCache[cacheKey] = result;
    renderHoursBadge(result);

  } catch(e) {
    console.warn('[Hours] Google Places hatası:', e);
    badge.style.display = 'none';
  }
}

function parseGoogleHours(oh, cacheKey) {
  const isOpen = oh.open_now;
  const periods = oh.periods || [];
  const weekdayText = oh.weekday_text || [];

  // Bugün kapanış saatini bul
  const now = new Date();
  const todayIdx = now.getDay(); // 0=Pazar
  const todayPeriod = periods.find(per => per.open && per.open.day === todayIdx);

  let detailText = '';
  if (isOpen && todayPeriod && todayPeriod.close) {
    const closeH = todayPeriod.close.time.slice(0,2);
    const closeM = todayPeriod.close.time.slice(2,4);
    const closeStr = `${closeH}:${closeM}`;
    detailText = lang === 'tr' ? `· ${closeStr}'e kadar` : `· Until ${closeStr}`;
  } else if (!isOpen && todayPeriod) {
    // Kapalıysa açılış saatini göster
    const openH = todayPeriod.open.time.slice(0,2);
    const openM = todayPeriod.open.time.slice(2,4);
    const openStr = `${openH}:${openM}`;
    detailText = lang === 'tr' ? `· ${openStr}'de açılıyor` : `· Opens at ${openStr}`;
  }

  return {
    fetchedAt: Date.now(),
    cacheKey,
    isOpen,
    badgeText: isOpen
      ? (lang === 'tr' ? 'Açık' : 'Open')
      : (lang === 'tr' ? 'Kapalı' : 'Closed'),
    detailText,
    weeklyText: weekdayText,
    periods
  };
}

function parseStoredHours(oh, cacheKey) {
  // Supabase'den gelen JSONB objesini parse et
  try {
    const parsed = typeof oh === 'string' ? JSON.parse(oh) : oh;
    return parseGoogleHours(parsed, cacheKey);
  } catch(e) {
    return null;
  }
}

function renderHoursBadge(data) {
  if (!data) return;
  const badge = document.getElementById('hours-badge');
  const mainEl = document.getElementById('hours-main');
  const detailEl = document.getElementById('hours-detail');
  const toggleBtn = document.getElementById('hours-toggle');
  if (!badge || !mainEl) return;

  badge.style.display = 'flex';
  badge.className = 'hours-badge ' + (data.isOpen ? 'open' : 'closed');
  mainEl.textContent = data.badgeText;
  if (detailEl) detailEl.textContent = data.detailText || '';

  // Haftalık program varsa toggle göster
  if (toggleBtn) {
    if (data.weeklyText && data.weeklyText.length > 0) {
      toggleBtn.style.display = 'block';
      // Haftalık listeyi hazırla ama gizli tut
      const weekEl = document.getElementById('hours-week');
      if (weekEl) {
        const todayIdx = new Date().getDay();
        const dayNames = getDayNames();
        // Google weekday_text Pazartesi başlıyor (0=Pzt), JS getDay() Pazar=0
        // weekday_text[0]=Monday, weekday_text[6]=Sunday
        const googleTodayIdx = todayIdx === 0 ? 6 : todayIdx - 1;
        weekEl.innerHTML = data.weeklyText.map((txt, i) => {
          const isToday = i === googleTodayIdx;
          return `<div class="hours-week-row${isToday ? ' today' : ''}">${txt}</div>`;
        }).join('');
      }
    } else {
      toggleBtn.style.display = 'none';
    }
  }
}

function toggleWeeklyHours() {
  const weekEl = document.getElementById('hours-week');
  const toggleBtn = document.getElementById('hours-toggle');
  if (!weekEl) return;
  const visible = weekEl.classList.toggle('visible');
  if (toggleBtn) toggleBtn.textContent = visible
    ? (lang === 'tr' ? '▴ Kapat' : '▴ Less')
    : (lang === 'tr' ? '▾ Tümü' : '▾ All');
}

async function saveGooglePlaceId(placeId, googlePlaceId) {
  try {
    const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token');
    if (!token) return;
    await fetch(`${SUPABASE_URL}/rest/v1/places?id=eq.${placeId}`, {
      method: 'PATCH',
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify({ google_place_id: googlePlaceId })
    });
  } catch(e) { console.warn('[Hours] saveGooglePlaceId hatası:', e); }
}

async function saveOpeningHours(placeId, googlePlaceId, oh) {
  try {
    const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token');
    if (!token) return;
    await fetch(`${SUPABASE_URL}/rest/v1/places?id=eq.${placeId}`, {
      method: 'PATCH',
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify({ google_place_id: googlePlaceId, opening_hours: oh })
    });
  } catch(e) { console.warn('[Hours] saveOpeningHours hatası:', e); }
}

// ─────────────────────────────────────────────────────────────────────────────

async function openMapModal() {"""

if "async function openMapModal() {" in html:
    html = html.replace("async function openMapModal() {", new6)
    patches.append("✓ Patch 6: fetchPlaceHours + renderHoursBadge + yardımcı fonksiyonlar eklendi")
else:
    patches.append("✗ Patch 6 BULUNAMADI")


# ══════════════════════════════════════════════════════════════════════════════
# Kaydet
# ══════════════════════════════════════════════════════════════════════════════
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*55}")
    print("CrewGuide patch22 — Çalışma saati + Açık badge")
    print('='*55)
    for p in patches:
        print(f"  {p}")
    changed = sum(1 for p in patches if p.startswith("✓"))
    failed  = sum(1 for p in patches if p.startswith("✗"))
    print(f"\n  Başarılı: {changed}/{len(patches)}")
    if failed:
        print(f"  ⚠️  {failed} patch uygulanamadı — kod değişmiş olabilir")
    print(f"\n✅ index.html güncellendi!")
    print("\n── Sonraki adımlar ─────────────────────────────────────")
    print("  1. Supabase SQL editöre gir ve şu sorguyu çalıştır:")
    print()
    print("     ALTER TABLE places")
    print("       ADD COLUMN IF NOT EXISTS google_place_id TEXT,")
    print("       ADD COLUMN IF NOT EXISTS opening_hours JSONB;")
    print()
    print("  2. index.html içinde GOOGLE_PLACES_KEY = '' satırını")
    print("     kendi API key'inle doldur.")
    print()
    print("  3. Google Cloud Console'da şu API'ları etkinleştir:")
    print("     • Places API (New)")
    print("     • Maps JavaScript API")
    print()
    print("  4. python deploy.py \"patch22: çalışma saati + açık badge\"")
    print('='*55 + '\n')
else:
    print("\n⚠️  Hiçbir değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
