#!/usr/bin/env python3
# CrewGuide patch2.py - Şehir filtresi + Admin silme düzeltmesi

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: loadPlaces() — şehir değişince eski yerleri temizle ──────────
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
      query += `&addr=ilike.*${encodeURIComponent(city)}*`;
    }
    const data = await sbFetch(query, { headers: { 'Prefer': '' } });

    // Şehir değişince places dizisini tamamen temizle
    // Sadece seçili şehre ait demo yerlerini koru
    places.length = 0;
    const demoCities = {
      'Seoul': ['mukbang','dongdaemun','gyeongbok','cafe'],
    };
    const keepIds = new Set(city && demoCities[city] ? demoCities[city] : []);
    // Demo verileri yeniden ekle (sadece seçili şehir için)
    const allDemos = [
      { id:'mukbang', cat:'food', subcat:'Restoran', emoji:'🥩', name:'Mukbang BBQ', addr:'Mapo-gu, Seoul', price:'$$', priceName:{tr:'Orta',en:'Mid-range'}, likes:47, rating:4.6, ratingCount:34, ratings:{5:18,4:10,3:4,2:1,1:1}, desc:{tr:'Sınırsız Kore barbekü, 90 dk.',en:'Unlimited Korean BBQ, 90 min.'} },
      { id:'dongdaemun', cat:'shopping', subcat:'Çanta & Valiz', emoji:'👜', name:'Dongdaemun Market', addr:'Jung-gu, Seoul', price:'$', priceName:{tr:'Uygun',en:'Budget'}, likes:31, rating:4.1, ratingCount:22, ratings:{5:8,4:9,3:3,2:1,1:1}, desc:{tr:'Tekstil ve aksesuar.',en:'Textiles and accessories.'} },
      { id:'gyeongbok', cat:'sightseeing', subcat:'Tarihi Yerler', emoji:'🏯', name:'Gyeongbokgung Palace', addr:'Jongno-gu, Seoul', price:'$', priceName:{tr:'Uygun',en:'Budget'}, likes:89, rating:4.8, ratingCount:61, ratings:{5:42,4:12,3:5,2:1,1:1}, desc:{tr:'Seoul\'ün en büyük sarayı.',en:'Seoul\'s largest palace.'} },
      { id:'cafe', cat:'food', subcat:'Kafe', emoji:'☕', name:'Cafe Bora', addr:'Insadong, Seoul', price:'$', priceName:{tr:'Uygun',en:'Budget'}, likes:55, rating:4.3, ratingCount:28, ratings:{5:14,4:9,3:3,2:1,1:1}, desc:{tr:'Mor renkli dondurma.',en:'Purple ice cream.'} },
    ];
    allDemos.forEach(d => { if (keepIds.has(d.id)) places.push(d); });

    if (!data || data.length === 0) {
      renderCards();
      return;
    }

    // Supabase'den gelen yerleri places dizisine ekle (duplicate olmaması için)
    const existingIds = new Set(places.map(p => p.id));"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: loadPlaces() şehir değişiminde temizleniyor")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── PATCH 2: adminDeletePlace() — token ile PATCH yap ────────────────────
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
    // Supabase'de gizle (is_hidden = true) — admin token ile
    const token = sessionStorage.getItem('sb_access_token');
    const res = await fetch(`${SUPABASE_URL}/rest/v1/places?id=eq.${p.id}`, {
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
      const err = await res.text();
      console.warn('[adminDelete]', err);
    }
  } catch(e) {
    console.warn('[adminDelete Supabase]', e);
  }"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: adminDeletePlace() token ile PATCH")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ── SONUÇ ────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide Patch 2 Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup2', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"\n✅ {applied} patch uygulandı, {fname} güncellendi!")
    print("📦 Yedek: index.html.backup2")
else:
    print("\n⚠ Değişiklik yapılmadı")

print("="*50 + "\n")
