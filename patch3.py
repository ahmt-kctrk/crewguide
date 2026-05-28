#!/usr/bin/env python3
# CrewGuide patch3.py - Şehir filtresi (syntax-safe) + Admin silme

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: loadPlaces() — şehir değişince Supabase yerlerini temizle ────
old1 = """async function loadPlaces(cityFilter) {
  try {
    const city = cityFilter || currentCity || null;
    let query = 'places?is_hidden=eq.false&order=created_at.desc&limit=100';
    if (city) {
      query += `&addr=ilike.*${encodeURIComponent(city)}*`;
    }
    const data = await sbFetch(query, { headers: { 'Prefer': '' } });
    if (!data || data.length === 0) {
      renderCards();
      return;
    }

    // Supabase'den gelen yerleri places dizisine ekle (duplicate olmaması için)
    const existingIds = new Set(places.map(p => p.id));"""

new1 = """async function loadPlaces(cityFilter) {
  try {
    const city = cityFilter || currentCity || null;
    let query = 'places?is_hidden=eq.false&order=created_at.desc&limit=100';
    if (city) {
      query += '&addr=ilike.*' + encodeURIComponent(city) + '*';
    }
    const data = await sbFetch(query, { headers: { 'Prefer': '' } });

    // Şehir değişince önceki Supabase yerlerini temizle (demo yerler kalır)
    const demoIds = ['mukbang','dongdaemun','gyeongbok','cafe'];
    for (let i = places.length - 1; i >= 0; i--) {
      if (!demoIds.includes(places[i].id)) {
        places.splice(i, 1);
      }
    }

    // Demo yerleri de şehre göre filtrele
    if (city && city !== 'Seoul') {
      for (let i = places.length - 1; i >= 0; i--) {
        places.splice(i, 1);
      }
    }

    if (!data || data.length === 0) {
      renderCards();
      return;
    }

    // Supabase'den gelen yerleri places dizisine ekle (duplicate olmaması için)
    const existingIds = new Set(places.map(p => p.id));"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: loadPlaces() şehir filtresi düzeltildi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── PATCH 2: adminDeletePlace() — token ile PATCH ─────────────────────────
old2 = """  try {
    // Supabase'de gizle (is_hidden = true)
    await sbFetch(`places?id=eq.${p.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_hidden: true })
    });
  } catch(e) {
    console.warn('[adminDelete Supabase]', e);
  }"""

new2 = """  try {
    const token = sessionStorage.getItem('sb_access_token');
    const res = await fetch(SUPABASE_URL + '/rest/v1/places?id=eq.' + p.id, {
      method: 'PATCH',
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + (token || SUPABASE_KEY),
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify({ is_hidden: true })
    });
    if (!res.ok) {
      console.warn('[adminDelete]', await res.text());
    }
  } catch(e) {
    console.warn('[adminDelete Supabase]', e);
  }"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: adminDeletePlace() token ile güncellendi")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide Patch 3 Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup3', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"\n✅ {applied} patch uygulandı, {fname} güncellendi!")
    print("📦 Yedek: index.html.backup3")
else:
    print("\n⚠ Değişiklik yapılmadı")

print("="*50 + "\n")
