#!/usr/bin/env python3
# CrewGuide patch6.py - city kolonu ile filtreleme + submitPlace city ekle

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: loadPlaces() — addr yerine city kolonu ile filtrele ──────────
old1 = """    let query = 'places?is_hidden=eq.false&order=created_at.desc&limit=100';
    if (city) {
      query += '&addr=ilike.*' + encodeURIComponent(city) + '*';
    }"""

new1 = """    let query = 'places?is_hidden=eq.false&order=created_at.desc&limit=100';
    if (city) {
      query += '&city=eq.' + encodeURIComponent(city);
    }"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: loadPlaces() city kolonu ile filtreliyor")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── PATCH 2: submitPlace() — Supabase'e city ekle ─────────────────────────
old2 = """        id: placeId,
        cat: selectedMainCat,
        subcat: subLabel,
        emoji: catEmojis[selectedMainCat],
        name, addr: addr || 'Seoul',
        price: priceVal,
        price_name_tr: (priceName[priceVal]||{}).tr || 'Uygun',
        price_name_en: (priceName[priceVal]||{}).en || 'Budget',
        desc_tr: desc || '', desc_en: desc || '',
        is_adult: isAdultContent,
        user_id: currentUser ? currentUser.id : null,
        is_hidden: false"""

new2 = """        id: placeId,
        cat: selectedMainCat,
        subcat: subLabel,
        emoji: catEmojis[selectedMainCat],
        name, addr: addr || currentCity || 'Seoul',
        city: currentCity || 'Seoul',
        price: priceVal,
        price_name_tr: (priceName[priceVal]||{}).tr || 'Uygun',
        price_name_en: (priceName[priceVal]||{}).en || 'Budget',
        desc_tr: desc || '', desc_en: desc || '',
        is_adult: isAdultContent,
        user_id: currentUser ? currentUser.id : null,
        is_hidden: false"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: submitPlace() city kolonu ekliyor")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide Patch 6 Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup6', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"\n✅ {applied} patch uygulandı!")
    print("📦 Yedek: index.html.backup6")
else:
    print("\n⚠ Değişiklik yapılmadı")

print("="*50 + "\n")
