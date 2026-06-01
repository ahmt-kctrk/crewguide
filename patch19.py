#!/usr/bin/env python3
# CrewGuide patch19.py
# 4 temel geliştirme:
#   1. Yorum sistemi  — giriş yapılmışsa ad alanını gizle, otomatik doldur
#   2. Bildirimler    — visitedCities: daha önce gittiğin şehre yeni yer eklenince bildirim
#   3. Puanlama       — detay ekranındaki yıldız giriş alanını daha belirgin göster
#   4. Para birimi    — canlı kur çekimi (exchangerate-api.com ücretsiz)

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
# PATCH 1: visitedCities — Ziyaret edilen şehirleri localStorage'a kaydet
# selectCity() fonksiyonuna ek
# ══════════════════════════════════════════════════════════════════════════════

old1 = """let currentCity = 'Seoul';
function selectCity(name, country, flag) {
  currentCity = name;
  const dot = document.getElementById('location-dot');
  const text = document.getElementById('location-text');
  dot.style.background = '#10b981';
if (text) text.textContent = flag + ' ' + name + ', ' + country;"""

new1 = """let currentCity = 'Seoul';

// ── ZIYARET EDİLEN ŞEHİRLER (Bildirim için) ──────────────────────────────────
function getVisitedCities() {
  try {
    return JSON.parse(localStorage.getItem('cg_visited_cities') || '[]');
  } catch { return []; }
}

function addVisitedCity(cityName) {
  if (!cityName) return;
  const cities = getVisitedCities();
  if (!cities.includes(cityName)) {
    cities.push(cityName);
    // En fazla 30 şehir tut
    if (cities.length > 30) cities.shift();
    localStorage.setItem('cg_visited_cities', JSON.stringify(cities));
  }
}

function hasVisitedCity(cityName) {
  return getVisitedCities().some(c => c.toLowerCase() === (cityName||'').toLowerCase());
}

function selectCity(name, country, flag) {
  currentCity = name;
  // Ziyaret edilen şehre ekle
  addVisitedCity(name);
  const dot = document.getElementById('location-dot');
  const text = document.getElementById('location-text');
  dot.style.background = '#10b981';
if (text) text.textContent = flag + ' ' + name + ', ' + country;"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: visitedCities sistemi eklendi (selectCity)")
else:
    patches.append("✗ Patch 1 BULUNAMADI (selectCity)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 2: Realtime bildirimde "daha önce gittiğin şehir" kontrolü
# Şu an sadece currentCity kontrolü var; biz hasVisitedCity de ekleyeceğiz
# ══════════════════════════════════════════════════════════════════════════════

old2 = """          if (isSameCity && name) {
            // Şu an aynı şehirdeyse anında göster
            showInAppNotification({
              title: lang==='tr' ? '📍 Yeni Yer Eklendi!' : '📍 New Place Added!',
              body: `${emoji} ${name}`,
              action: () => {"""

new2 = """          if (isSameCity && name) {
            // Şu an aynı şehirdeyse anında göster
            showInAppNotification({
              title: lang==='tr' ? '📍 Yeni Yer Eklendi!' : '📍 New Place Added!',
              body: `${emoji} ${name}`,
              action: () => {"""

# Bu zaten doğru, ikinci kısma bakayım

old2b = """          } else if (name && placeCity) {
            // Farklı şehirse daha sessiz bildirim
            showInAppNotification({
              title: lang==='tr' ? `✈️ ${placeCity} için yeni yer!` : `✈️ New place in ${placeCity}!`,
              body: `${emoji} ${name}`,
              quiet: true
            });
          }"""

new2b = """          } else if (name && placeCity) {
            // Farklı şehir — daha önce gittiyse bildirim ver, gitmediyse sessiz geç
            const wasVisited = hasVisitedCity(placeCity);
            if (wasVisited) {
              showInAppNotification({
                title: lang==='tr'
                  ? `✈️ Gittiğin ${placeCity}'a yeni yer eklendi!`
                  : `✈️ New place in ${placeCity} — you've been there!`,
                body: `${emoji} ${name}`,
                quiet: true
              });
            }
            // Hiç gitmemişse bildirim gösterme
          }"""

if old2b in html:
    html = html.replace(old2b, new2b)
    patches.append("✓ Patch 2: Ziyaret edilen şehir bildirim filtresi eklendi")
else:
    patches.append("✗ Patch 2 BULUNAMADI (else if placeCity)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 3: Yorum sistemi — Giriş yapılmışsa kullanıcı adı alanını otomatik
#          doldur ve readonly yap; giriş yapılmamışsa normal göster
# loadComments çağrısının ardından çalışacak prefillCommentUsername güncellemesi
# ══════════════════════════════════════════════════════════════════════════════

old3 = """function prefillCommentUsername() {
  const input = document.getElementById('comment-username');
  if (input && !input.value && currentProfile && currentProfile.username) {
    input.value = currentProfile.username;
    input.style.color = 'var(--text-muted)'; // görsel ipucu
  }
}"""

new3 = """function prefillCommentUsername() {
  const input = document.getElementById('comment-username');
  if (!input) return;

  if (currentProfile && currentProfile.username) {
    // Giriş yapılmış → otomatik doldur, readonly yap, görsel ipucu
    input.value = currentProfile.username;
    input.readOnly = true;
    input.style.background = 'var(--cream-dark)';
    input.style.color = 'var(--text-secondary)';
    input.style.cursor = 'default';
    input.title = lang==='tr' ? 'Profil adın kullanılıyor' : 'Using your profile name';

    // Küçük "profil" etiketi
    const row = input.parentNode;
    if (row && !row.querySelector('.comment-profile-badge')) {
      const badge = document.createElement('span');
      badge.className = 'comment-profile-badge';
      badge.style.cssText = 'font-size:10px;color:var(--gold);font-weight:600;white-space:nowrap;flex-shrink:0;';
      badge.textContent = '✓ ' + (lang==='tr' ? 'Profil' : 'Profile');
      row.insertBefore(badge, input.nextSibling);
    }
  } else {
    // Giriş yapılmamış → düzenlenebilir
    input.readOnly = false;
    input.style.background = '';
    input.style.color = '';
    input.style.cursor = '';
    const badge = input.parentNode && input.parentNode.querySelector('.comment-profile-badge');
    if (badge) badge.remove();
  }
}"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: Yorum kullanıcı adı otomatik doldur + readonly")
else:
    patches.append("✗ Patch 3 BULUNAMADI (prefillCommentUsername)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 4: Puanlama — detay ekranındaki yıldız bölümünü daha belirgin yap
# star-input-row'a label ekle, henüz oy verilmemişse CTA mesajı göster
# ══════════════════════════════════════════════════════════════════════════════

old4 = """  .star-input-row { display: flex; align-items: center; gap: 8px; padding-top: 10px; border-top: 1px solid var(--border); }
  .star-input-label { font-size: 12px; color: var(--text-secondary); flex-shrink: 0; }"""

new4 = """  .star-input-row { display: flex; align-items: center; gap: 8px; padding-top: 12px; border-top: 1.5px solid var(--border); margin-top: 4px; }
  .star-input-label { font-size: 12px; font-weight: 600; color: var(--text-primary); flex-shrink: 0; }
  .star-input-cta { font-size: 11px; color: var(--text-muted); padding: 4px 8px; background: var(--cream-dark); border-radius: 6px; }"""

if old4 in html:
    html = html.replace(old4, new4)
    patches.append("✓ Patch 4a: star-input-row stil güncellendi")
else:
    patches.append("✗ Patch 4a BULUNAMADI (star-input-row CSS)")

# Puanlama label metnini iyileştir — renderRatingBar içinde
old4b = """  const ratingTitles = {tr:'Puan',en:'Rating',de:'Bewertung',fr:'Note',es:'Calificación',ar:'التقييم',ja:'評価',ko:'평점',zh:'评分'};"""

new4b = """  // Kullanıcı zaten oy verdiyse label değiştir
  const userRatedAlready = p.userRating && p.userRating > 0;
  const ratingTitles = {tr:'Puan',en:'Rating',de:'Bewertung',fr:'Note',es:'Calificación',ar:'التقييم',ja:'評価',ko:'평점',zh:'评分'};"""

if old4b in html:
    html = html.replace(old4b, new4b)
    patches.append("✓ Patch 4b: userRatedAlready flag eklendi")
else:
    patches.append("✗ Patch 4b BULUNAMADI (ratingTitles)")

# Star input label güncelle
old4c = """  const starLabel = document.getElementById('star-input-label');
  if (starLabel) starLabel.textContent = lang === 'tr' ? 'Senin Puanın:' : 'Your Rating:';"""

new4c = """  const starLabel = document.getElementById('star-input-label');
  if (starLabel) {
    if (userRatedAlready) {
      starLabel.textContent = lang === 'tr' ? `✓ ${p.userRating} yıldız verdin` : `✓ You rated ${p.userRating} ★`;
      starLabel.style.color = 'var(--gold)';
    } else {
      starLabel.textContent = lang === 'tr' ? 'Sen de puan ver:' : 'Rate this place:';
      starLabel.style.color = '';
    }
  }"""

if old4c in html:
    html = html.replace(old4c, new4c)
    patches.append("✓ Patch 4c: star-input-label dinamik metin")
else:
    patches.append("✗ Patch 4c BULUNAMADI (starLabel textContent)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 5: Para birimi — Canlı kur çekimi
# updateCurrencyBadge çağrıldığında arka planda ExchangeRate-API'den kur çek
# Ücretsiz endpoint: https://open.er-api.com/v6/latest/USD
# ══════════════════════════════════════════════════════════════════════════════

old5 = """function updateCurrencyBadge(cityName) {
  const cur = getCurrencyForCity(cityName);
  currentCurrency = cur;
  const symEl = document.getElementById('currency-symbol');
  const codeEl = document.getElementById('currency-code');
  if (symEl) symEl.textContent = cur.symbol;
  if (codeEl) codeEl.textContent = cur.code;

  // Badge'e kur bilgisi tooltip ekle
  const badge = document.getElementById('currency-badge');
  if (badge) {
    const rate = (1 / cur.rate).toFixed(cur.rate < 0.01 ? 0 : cur.rate < 0.1 ? 1 : 2);
    badge.title = `1 USD ≈ ${rate} ${cur.symbol}`;
  }

  // Kur bilgi satırı varsa güncelle
  const rateEl = document.getElementById('currency-rate-hint');
  if (rateEl) {
    const rate = (1 / cur.rate).toFixed(cur.rate < 0.01 ? 0 : cur.rate < 0.1 ? 1 : 2);
    rateEl.textContent = `1 USD ≈ ${rate} ${cur.symbol}`;
  }
}"""

new5 = """// ── CANLI KUR SİSTEMİ ────────────────────────────────────────────────────────
// open.er-api.com — ücretsiz, kayıt gerektirmez, 1500 istek/ay
let liveRatesCache = null;      // { USD: 1, EUR: 0.92, ... }
let liveRatesFetchedAt = 0;     // timestamp (ms)
const LIVE_RATES_TTL = 3600000; // 1 saat cache

async function fetchLiveRates() {
  // Cache geçerliyse tekrar çekme
  if (liveRatesCache && Date.now() - liveRatesFetchedAt < LIVE_RATES_TTL) {
    return liveRatesCache;
  }
  try {
    const res = await fetch('https://open.er-api.com/v6/latest/USD', { cache: 'force-cache' });
    if (!res.ok) return null;
    const data = await res.json();
    if (data && data.rates) {
      liveRatesCache = data.rates;
      liveRatesFetchedAt = Date.now();
      console.log('[Currency] Canlı kurlar alındı:', Object.keys(data.rates).length, 'para birimi');
      return liveRatesCache;
    }
  } catch(e) {
    console.warn('[Currency] Canlı kur alınamadı, yerel kurlar kullanılıyor:', e.message);
  }
  return null;
}

function applyLiveRate(cur, rates) {
  if (!rates || !cur.code) return cur;
  const liveRate = rates[cur.code];
  if (liveRate && liveRate > 0) {
    // 1 USD = liveRate birim yerel para → 1 yerel = 1/liveRate USD
    return { ...cur, rate: 1 / liveRate, _live: true };
  }
  return cur;
}

function updateCurrencyBadge(cityName) {
  let cur = getCurrencyForCity(cityName);
  currentCurrency = cur;
  const symEl = document.getElementById('currency-symbol');
  const codeEl = document.getElementById('currency-code');
  if (symEl) symEl.textContent = cur.symbol;
  if (codeEl) codeEl.textContent = cur.code;

  // Badge'e kur bilgisi tooltip ekle
  const badge = document.getElementById('currency-badge');
  const rateEl = document.getElementById('currency-rate-hint');
  function displayRate(c) {
    const rate = (1 / c.rate).toFixed(c.rate < 0.01 ? 0 : c.rate < 0.1 ? 1 : 2);
    const liveTag = c._live ? ' ●' : '';
    if (badge) badge.title = `1 USD ≈ ${rate} ${c.symbol}${liveTag}`;
    if (rateEl) rateEl.textContent = `1 USD ≈ ${rate} ${c.symbol}${liveTag}`;
  }

  // Önce yerel kurla göster (anında)
  displayRate(cur);

  // Arka planda canlı kur çek ve güncelle
  fetchLiveRates().then(rates => {
    if (!rates) return;
    const liveCur = applyLiveRate(cur, rates);
    currentCurrency = liveCur;
    displayRate(liveCur);
    if (symEl) symEl.textContent = liveCur.symbol;
    if (codeEl) codeEl.textContent = liveCur.code;
  }).catch(() => {});
}"""

if old5 in html:
    html = html.replace(old5, new5)
    patches.append("✓ Patch 5: Canlı kur sistemi eklendi (ExchangeRate-API)")
else:
    patches.append("✗ Patch 5 BULUNAMADI (updateCurrencyBadge)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 6: showCurrencyModal — Canlı kur bilgisini göster, son güncelleme saati
# ══════════════════════════════════════════════════════════════════════════════

old6 = """      <div style="font-size:10px;color:var(--text-muted);margin-top:10px;text-align:center;">${lang==='tr'?'Kurlar yaklaşık değerdir, değişebilir.':'Rates are approximate and may vary.'}</div>"""

new6 = """      <div style="font-size:10px;color:var(--text-muted);margin-top:10px;text-align:center;" id="currency-modal-info">
        ${liveRatesCache
          ? (lang==='tr'
              ? '● Canlı kur · ' + new Date(liveRatesFetchedAt).toLocaleTimeString(lang==='tr'?'tr-TR':'en-US', {hour:'2-digit',minute:'2-digit'}) + ' itibarıyla'
              : '● Live rate · as of ' + new Date(liveRatesFetchedAt).toLocaleTimeString('en-US', {hour:'2-digit',minute:'2-digit'}))
          : (lang==='tr'?'Kurlar yaklaşık değerdir, değişebilir.':'Rates are approximate and may vary.')}
      </div>"""

if old6 in html:
    html = html.replace(old6, new6)
    patches.append("✓ Patch 6: Para birimi modalında canlı kur bilgisi")
else:
    patches.append("✗ Patch 6 BULUNAMADI (currency-modal-info)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 7: Bildirim ekranına "Takip Ettiğin Şehirler" bölümü ekle
# Mevcut notif screen'deki boş alanı doldur
# ══════════════════════════════════════════════════════════════════════════════

old7 = """  <!-- SCREEN: NOTIFICATIONS -->
  <div class="screen" id="screen-notif">
    <div class="status-bar">
      <span class="status-time">09:41</span>
      <div class="status-icons"><div class="status-icon signal"></div><div class="status-icon battery"></div></div>
    </div>
    <div class="navy-header">
      <div class="nav-back" onclick="goTo('screen-home')">← </div>
      <div class="header-title font-display" id="notif-title">Bildirimler</div>
      <div class="header-sub" id="notif-sub">Son eklenen yerler</div>
    </div>"""

new7 = """  <!-- SCREEN: NOTIFICATIONS -->
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
    <!-- Ziyaret edilen şehirler özeti -->
    <div id="visited-cities-bar" style="margin:0 16px;margin-top:12px;padding:10px 12px;background:var(--navy);border-radius:var(--radius-sm);display:none;">
      <div style="font-family:'Syne',sans-serif;font-size:11px;font-weight:600;color:rgba(255,255,255,0.5);margin-bottom:6px;" id="visited-bar-label">✈️ GİTTİĞİN ŞEHİRLER</div>
      <div id="visited-cities-list" style="display:flex;flex-wrap:wrap;gap:5px;"></div>
      <div style="font-size:10px;color:rgba(255,255,255,0.3);margin-top:6px;" id="visited-bar-hint">Bu şehirlere yeni yer eklenince bildirim alırsın</div>
    </div>"""

if old7 in html:
    html = html.replace(old7, new7)
    patches.append("✓ Patch 7: Bildirim ekranına 'Gittiğin Şehirler' bölümü eklendi")
else:
    patches.append("✗ Patch 7 BULUNAMADI (screen-notif header)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 8: Bildirim ekranı açılınca visitedCities render et
# goTo fonksiyonu içinde screen-notif'e gelinince çağır
# ══════════════════════════════════════════════════════════════════════════════

old8 = """function goTo(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const target = document.getElementById(id);
  if (target) target.classList.add('active');"""

new8 = """function goTo(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const target = document.getElementById(id);
  if (target) target.classList.add('active');

  // Bildirim ekranı açılınca ziyaret edilen şehirleri göster
  if (id === 'screen-notif') {
    renderVisitedCitiesBar();
  }"""

if old8 in html:
    html = html.replace(old8, new8)
    patches.append("✓ Patch 8: goTo → screen-notif açılınca visitedCities render")
else:
    patches.append("✗ Patch 8 BULUNAMADI (function goTo)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 9: renderVisitedCitiesBar fonksiyonu ekle
# showCurrencyInfo'nun hemen üstüne
# ══════════════════════════════════════════════════════════════════════════════

old9 = """function showCurrencyInfo() {"""

new9 = """// ── ZİYARET EDİLEN ŞEHİRLER RENDER ──────────────────────────────────────────
function renderVisitedCitiesBar() {
  const cities = getVisitedCities();
  const bar = document.getElementById('visited-cities-bar');
  const list = document.getElementById('visited-cities-list');
  const label = document.getElementById('visited-bar-label');
  const hint = document.getElementById('visited-bar-hint');
  if (!bar || !list) return;

  // Çeviri
  if (label) label.textContent = lang==='tr' ? '✈️ GİTTİĞİN ŞEHİRLER' : '✈️ CITIES YOU\'VE VISITED';
  if (hint) hint.textContent = lang==='tr'
    ? 'Bu şehirlere yeni yer eklenince bildirim alırsın'
    : 'You\'ll be notified when new places are added';

  if (!cities.length) {
    bar.style.display = 'none';
    return;
  }

  bar.style.display = 'block';
  list.innerHTML = cities.map(city => `
    <span onclick="selectCityFromNotif('${city.replace(/'/g, "\\'")}')" style="
      display:inline-flex;align-items:center;gap:4px;
      background:rgba(255,255,255,0.1);color:#fff;
      border-radius:20px;padding:3px 9px;
      font-size:11px;font-family:'Syne',sans-serif;font-weight:500;cursor:pointer;
      border:1px solid rgba(255,255,255,0.15);
      transition:background 0.15s;">
      ✈️ ${city}
      <span onclick="removeVisitedCity(event, '${city.replace(/'/g, "\\'")}')"
        style="font-size:10px;opacity:0.5;margin-left:2px;cursor:pointer;" title="${lang==='tr'?'Kaldır':'Remove'}">✕</span>
    </span>`).join('');
}

function selectCityFromNotif(cityName) {
  // Şehir seç ve ana sayfaya git
  const cur = getCurrencyForCity(cityName);
  currentCity = cityName;
  currentCurrency = cur;
  updateCurrencyBadge(cityName);
  loadPlaces(cityName);
  const text = document.getElementById('location-text');
  if (text) text.textContent = cityName;
  goTo('screen-home');
}

function removeVisitedCity(event, cityName) {
  event.stopPropagation();
  const cities = getVisitedCities().filter(c => c !== cityName);
  localStorage.setItem('cg_visited_cities', JSON.stringify(cities));
  renderVisitedCitiesBar();
}

function showCurrencyInfo() {"""

if old9 in html:
    html = html.replace(old9, new9)
    patches.append("✓ Patch 9: renderVisitedCitiesBar + removeVisitedCity fonksiyonları")
else:
    patches.append("✗ Patch 9 BULUNAMADI (showCurrencyInfo)")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 10: App başlangıcında Seoul'ü ziyaret edilen şehirlere ekle (default)
# ══════════════════════════════════════════════════════════════════════════════

old10 = """updateCurrencyBadge('Seoul');
// Supabase'den Seoul yerlerini yükle
loadPlaces('Seoul');"""

new10 = """updateCurrencyBadge('Seoul');
// Default şehri ziyaret edilenler listesine ekle
addVisitedCity('Seoul');
// Supabase'den Seoul yerlerini yükle
loadPlaces('Seoul');"""

if old10 in html:
    html = html.replace(old10, new10)
    patches.append("✓ Patch 10: Başlangıç Seoul ziyaret listesine eklendi")
else:
    patches.append("✗ Patch 10 BULUNAMADI (updateCurrencyBadge Seoul)")

# ══════════════════════════════════════════════════════════════════════════════
# SONUÇ
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("CrewGuide Patch 19 Sonuçları")
print("="*60)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup19', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    failed  = len([p for p in patches if p.startswith("✗")])
    print(f"\n✅ {applied} patch uygulandı!")
    if failed:
        print(f"⚠️  {failed} patch bulunamadı — kontrol et")
    print("📦 Yedek: index.html.backup19")
else:
    print("\n⚠ Değişiklik yapılmadı — hiç patch eşleşmedi")
print("="*60 + "\n")
