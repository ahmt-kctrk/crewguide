#!/usr/bin/env python3
# CrewGuide patch31.py — Sürüklenebilir pin ile konum seçici
# 📍 butonuna basınca harita açılır, pin sürüklenebilir, adres otomatik dolar

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
# PATCH 1 — CSS: Konum seçici modal stilleri
# ══════════════════════════════════════════════════════════════════════════════
old1 = "  /* Admin sekmeleri */"
new1 = """  /* Konum seçici modal */
  .location-picker-modal {
    position: fixed; inset: 0; z-index: 9999;
    background: var(--white);
    display: flex; flex-direction: column;
    animation: slideUp 0.25s ease;
  }
  .location-picker-header {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 16px; border-bottom: 1px solid var(--border);
    flex-shrink: 0; background: var(--white);
  }
  .location-picker-title {
    font-size: 15px; font-weight: 700; color: var(--navy);
    font-family: 'Syne', sans-serif; flex: 1;
  }
  .location-picker-subtitle {
    font-size: 11px; color: var(--text-muted); margin-top: 2px;
  }
  #location-picker-map {
    flex: 1; min-height: 0;
  }
  .location-picker-footer {
    padding: 12px 16px; border-top: 1px solid var(--border);
    background: var(--white); flex-shrink: 0;
  }
  .location-picker-addr {
    font-size: 12px; color: var(--text-secondary);
    margin-bottom: 10px; min-height: 16px;
    display: flex; align-items: center; gap: 6px;
    transition: opacity 0.2s;
  }
  .location-picker-addr.loading { opacity: 0.5; }
  .picker-confirm-btn {
    width: 100%; padding: 14px; border-radius: var(--radius);
    background: var(--navy); color: #fff; border: none;
    font-size: 15px; font-weight: 700; font-family: 'Syne', sans-serif;
    cursor: pointer; transition: opacity 0.2s;
  }
  .picker-confirm-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  /* Admin sekmeleri */"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: CSS eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 2 — HTML: 📍 butonunu harita açacak şekilde güncelle
# ══════════════════════════════════════════════════════════════════════════════
old2 = """          <button onclick="fillCurrentLocation()" id="btn-gps-location" title="Mevcut konumu kullan" style="
            flex-shrink:0; width:44px; height:44px; border-radius:var(--radius-sm);
            background:var(--navy); color:#fff; border:none; cursor:pointer;
            font-size:18px; display:flex; align-items:center; justify-content:center;
            transition:opacity 0.2s;">📍</button>"""

new2 = """          <button onclick="openLocationPicker()" id="btn-gps-location" title="Haritadan konum seç" style="
            flex-shrink:0; width:44px; height:44px; border-radius:var(--radius-sm);
            background:var(--navy); color:#fff; border:none; cursor:pointer;
            font-size:18px; display:flex; align-items:center; justify-content:center;
            transition:opacity 0.2s;">🗺</button>"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: 📍 butonu harita açacak şekilde güncellendi")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 3 — JS: openLocationPicker + closeLocationPicker fonksiyonları
# fillCurrentLocation fonksiyonunun hemen üstüne
# ══════════════════════════════════════════════════════════════════════════════
old3 = "async function fillCurrentLocation() {"
new3 = """// ── KONUM SEÇİCİ (sürüklenebilir pin) ───────────────────────────────────────
let pickerMap = null;
let pickerMarker = null;
let pickerLat = null;
let pickerLon = null;
let pickerAddrTimer = null;

async function openLocationPicker() {
  // Eski modal varsa kaldır
  const old = document.getElementById('location-picker-modal');
  if (old) old.remove();
  if (pickerMap) { pickerMap.remove(); pickerMap = null; pickerMarker = null; }

  const modal = document.createElement('div');
  modal.id = 'location-picker-modal';
  modal.className = 'location-picker-modal';
  modal.innerHTML = `
    <div class="location-picker-header">
      <button class="map-close-btn" onclick="closeLocationPicker()">←</button>
      <div style="flex:1;">
        <div class="location-picker-title">${lang==='tr'?'Konumu Seç':'Pick Location'}</div>
        <div class="location-picker-subtitle">${lang==='tr'?'Pini sürükleyerek konumu ayarla':'Drag the pin to adjust the location'}</div>
      </div>
    </div>
    <div id="location-picker-map"></div>
    <div class="location-picker-footer">
      <div class="location-picker-addr" id="picker-addr-text">
        <span>📍</span>
        <span id="picker-addr-label">${lang==='tr'?'Konum alınıyor...':'Getting location...'}</span>
      </div>
      <button class="picker-confirm-btn" id="picker-confirm-btn" onclick="confirmPickedLocation()" disabled>
        ${lang==='tr'?'Bu Konumu Kullan ✓':'Use This Location ✓'}
      </button>
    </div>
  `;

  document.getElementById('app').appendChild(modal);

  // Başlangıç koordinatı: GPS veya şehir merkezi
  const startLat = pickerLat || 48.8566;
  const startLon = pickerLon || 2.3522;

  setTimeout(async () => {
    pickerMap = L.map('location-picker-map', {
      center: [startLat, startLon],
      zoom: 15,
      zoomControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
      maxZoom: 19
    }).addTo(pickerMap);

    // Sürüklenebilir marker
    const markerIcon = L.divIcon({
      html: `<div style="
        width:36px;height:36px;border-radius:50% 50% 50% 0;
        background:var(--navy,#0f1729);border:3px solid white;
        transform:rotate(-45deg);box-shadow:0 2px 8px rgba(0,0,0,0.3);
        display:flex;align-items:center;justify-content:center;">
        <span style="transform:rotate(45deg);font-size:16px;">📍</span>
      </div>`,
      className: '',
      iconSize: [36, 36],
      iconAnchor: [18, 36],
    });

    pickerMarker = L.marker([startLat, startLon], {
      icon: markerIcon,
      draggable: true,
    }).addTo(pickerMap);

    pickerLat = startLat;
    pickerLon = startLon;

    // Pin sürüklenince adres güncelle
    pickerMarker.on('dragend', async (e) => {
      const pos = e.target.getLatLng();
      pickerLat = pos.lat;
      pickerLon = pos.lng;
      await updatePickerAddress(pos.lat, pos.lng);
    });

    // Haritaya tıklayınca pin oraya gitsin
    pickerMap.on('click', async (e) => {
      pickerLat = e.latlng.lat;
      pickerLon = e.latlng.lng;
      pickerMarker.setLatLng([pickerLat, pickerLon]);
      await updatePickerAddress(pickerLat, pickerLon);
    });

    pickerMap.invalidateSize();

    // GPS ile başla
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          pickerLat = pos.coords.latitude;
          pickerLon = pos.coords.longitude;
          pickerMarker.setLatLng([pickerLat, pickerLon]);
          pickerMap.setView([pickerLat, pickerLon], 16);
          await updatePickerAddress(pickerLat, pickerLon);
        },
        () => {
          // GPS izni yok — mevcut konumda kal
          updatePickerAddress(startLat, startLon);
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    } else {
      updatePickerAddress(startLat, startLon);
    }
  }, 150);
}

async function updatePickerAddress(lat, lon) {
  const label = document.getElementById('picker-addr-label');
  const addrEl = document.getElementById('picker-addr-text');
  const btn = document.getElementById('picker-confirm-btn');

  if (label) label.textContent = lang==='tr'?'Adres aranıyor...':'Looking up address...';
  if (addrEl) addrEl.classList.add('loading');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=${lang}`,
      { headers: { 'User-Agent': 'CrewGuide/1.0' } }
    );
    const data = await res.json();
    const a = data.address || {};
    const parts = [];
    if (a.road || a.pedestrian || a.street) parts.push(a.road || a.pedestrian || a.street);
    if (a.neighbourhood || a.suburb || a.district) parts.push(a.neighbourhood || a.suburb || a.district);
    if (a.city || a.town || a.village || a.county) parts.push(a.city || a.town || a.village || a.county);
    if (a.country) parts.push(a.country);

    const addr = parts.join(', ') || data.display_name || `${lat.toFixed(5)}, ${lon.toFixed(5)}`;

    if (label) label.textContent = addr;
    if (addrEl) addrEl.classList.remove('loading');
    if (btn) btn.disabled = false;

    // Adresi global sakla
    window._pickerResolvedAddr = addr;

  } catch(e) {
    const fallback = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
    if (label) label.textContent = fallback;
    if (addrEl) addrEl.classList.remove('loading');
    if (btn) btn.disabled = false;
    window._pickerResolvedAddr = fallback;
  }
}

function confirmPickedLocation() {
  const input = document.getElementById('input-place-addr');
  const addr = window._pickerResolvedAddr;
  if (input && addr) {
    input.value = addr;
    showToast(lang==='tr'?'📍 Konum eklendi!':'📍 Location added!');
  }
  closeLocationPicker();
}

function closeLocationPicker() {
  const modal = document.getElementById('location-picker-modal');
  if (modal) modal.remove();
  if (pickerMap) { pickerMap.remove(); pickerMap = null; pickerMarker = null; }
}

// ─────────────────────────────────────────────────────────────────────────────

async function fillCurrentLocation() {"""

if "async function fillCurrentLocation() {" in html:
    html = html.replace("async function fillCurrentLocation() {", new3)
    patches.append("✓ Patch 3: openLocationPicker + yardımcı fonksiyonlar eklendi")
else:
    patches.append("✗ Patch 3 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# Kaydet
# ══════════════════════════════════════════════════════════════════════════════
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*58}")
    print("CrewGuide patch31 — Sürüklenebilir pin konum seçici")
    print('='*58)
    for p in patches:
        print(f"  {p}")
    print(f"""
  python deploy.py "patch31: sürüklenebilir pin konum seçici"

  Yeni akış:
  1. Yer ekle → 🗺 butonuna bas
  2. Harita modal açılır, GPS ile konuma odaklanır
  3. Pin sürüklenebilir veya haritaya tıklanabilir
  4. Alt kısımda adres otomatik güncellenir
  5. "Bu Konumu Kullan" → adres alanı dolar
{'='*58}
""")
else:
    print("\n⚠️  Değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
