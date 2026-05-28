#!/usr/bin/env python3
# CrewGuide patch8.py - GPS şehir tespiti düzeltmesi

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: useCurrentLocation() — ilçe değil şehir kullan ──────────────
old1 = """        const city = data.address.city || data.address.town || data.address.village || '';
        const country = data.address.country || '';
        dot.style.background = '#10b981';
        text.textContent = '📍 ' + city + (country ? ', ' + country : '');
        const addSub = document.getElementById('add-sub');
        if (addSub) addSub.textContent = city + ' · ' + (lang==='tr'?'Deneyimini paylaş':'Share your experience');
        // Şehri güncelle ve yerleri yükle
        currentCity = city;
        currentCurrency = getCurrencyForCity(city);
        updateCurrencyBadge(city);
        loadPlaces(city);"""

new1 = """        // Önce büyük şehir adını al, sonra ilçeyi göster
        const cityName = data.address.city || data.address.province || data.address.state || '';
        const district = data.address.town || data.address.suburb || data.address.village || '';
        const country = data.address.country || '';
        const displayName = district ? district + ', ' + cityName : cityName;
        dot.style.background = '#10b981';
        text.textContent = '📍 ' + (displayName || cityName) + (country ? ', ' + country : '');
        const addSub = document.getElementById('add-sub');
        if (addSub) addSub.textContent = (cityName || district) + ' · ' + (lang==='tr'?'Deneyimini paylaş':'Share your experience');
        // Şehir adıyla yerleri yükle ve para birimini güncelle
        currentCity = cityName || district;
        currentCurrency = getCurrencyForCity(currentCity);
        updateCurrencyBadge(currentCity);
        loadPlaces(currentCity);"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: GPS şehir adı düzeltildi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── PATCH 2: currencyDB'ye İstanbul varyantları ekle ─────────────────────
old2 = """  'İstanbul':    { symbol:'₺',  code:'TRY', rate:0.028,  name:{tr:'Türk Lirası',   en:'Turkish Lira'} },"""

new2 = """  'İstanbul':    { symbol:'₺',  code:'TRY', rate:0.028,  name:{tr:'Türk Lirası',   en:'Turkish Lira'} },
  'Istanbul':    { symbol:'₺',  code:'TRY', rate:0.028,  name:{tr:'Türk Lirası',   en:'Turkish Lira'} },
  'Türkiye':     { symbol:'₺',  code:'TRY', rate:0.028,  name:{tr:'Türk Lirası',   en:'Turkish Lira'} },
  'Turkey':      { symbol:'₺',  code:'TRY', rate:0.028,  name:{tr:'Türk Lirası',   en:'Turkish Lira'} },"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: currencyDB İstanbul varyantları eklendi")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide Patch 8 Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup8', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"\n✅ {applied} patch uygulandı!")
    print("📦 Yedek: index.html.backup8")
else:
    print("\n⚠ Değişiklik yapılmadı")

print("="*50 + "\n")
