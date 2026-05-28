#!/usr/bin/env python3
# CrewGuide patch7.py - useCurrentLocation() düzeltmesi

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: useCurrentLocation() — loadPlaces + currency güncelle ────────
old1 = """        const city = data.address.city || data.address.town || data.address.village || '';
        const country = data.address.country || '';
        dot.style.background = '#10b981';
        text.textContent = '📍 ' + city + (country ? ', ' + country : '');
        const addSub = document.getElementById('add-sub');
        if (addSub) addSub.textContent = city + ' · ' + (lang==='tr'?'Deneyimini paylaş':'Share your experience');"""

new1 = """        const city = data.address.city || data.address.town || data.address.village || '';
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

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: useCurrentLocation() loadPlaces + currency eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide Patch 7 Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup7', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"\n✅ {applied} patch uygulandı!")
    print("📦 Yedek: index.html.backup7")
else:
    print("\n⚠ Değişiklik yapılmadı")

print("="*50 + "\n")
