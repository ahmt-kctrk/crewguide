#!/usr/bin/env python3
# CrewGuide patch4.py

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: Demo yerleri JS'den kaldır, places array boş başlasın ────────
old1 = """const places = [
  { id:'mukbang', cat:'food', subcat:'Restoran', emoji:'🥩', name:'Mukbang BBQ', addr:'Mapo-gu, Seoul', price:'$$', priceName:{tr:'Orta',en:'Mid-range'}, likes:47, rating:4.6, ratingCount:34, ratings:{5:18,4:10,3:4,2:1,1:1}, desc:{tr:'Sınırsız Kore barbekü, 90 dk. Akşam yoğun olur, öğlen git. Ödeme nakit tercih ediyorlar.',en:'Unlimited Korean BBQ, 90 min. Gets crowded in evenings, go for lunch. Cash payment preferred.'} },
  { id:'dongdaemun', cat:'shopping', subcat:'Çanta & Valiz', emoji:'👜', name:'Dongdaemun Market', addr:'Jung-gu, Seoul', price:'$', priceName:{tr:'Uygun',en:'Budget'}, likes:31, rating:4.1, ratingCount:22, ratings:{5:8,4:9,3:3,2:1,1:1}, desc:{tr:'Tekstil ve aksesuar için harika. Toplu alımda fiyat pazarlığı yapılabilir. Gece de açık.',en:'Great for textiles and accessories. Bargain for bulk purchases. Open at night too.'} },
  { id:'gyeongbok', cat:'sightseeing', subcat:'Tarihi Yerler', emoji:'🏯', name:'Gyeongbokgung Palace', addr:'Jongno-gu, Seoul', price:'$', priceName:{tr:'Uygun',en:'Budget'}, likes:89, rating:4.8, ratingCount:61, ratings:{5:42,4:12,3:5,2:1,1:1}, desc:{tr:'Seoul\'ün en büyük sarayı. Nöbet değişimi sabah 10\'da. Hanbok kiralayıp gir, ücretsiz!',en:'Seoul\'s largest palace. Guard changing at 10am. Rent a Hanbok to enter for free!'} },
  { id:'cafe', cat:'food', subcat:'Kafe', emoji:'☕', name:'Cafe Bora', addr:'Insadong, Seoul', price:'$', priceName:{tr:'Uygun',en:'Budget'}, likes:55, rating:4.3, ratingCount:28, ratings:{5:14,4:9,3:3,2:1,1:1}, desc:{tr:'Mor renkli dondurma ve latte\'siyle ünlü. Instagram için mükemmel. Erken git!',en:'Famous for purple-colored ice cream and lattes. Perfect for Instagram. Go early!'} },
];"""

new1 = """const places = [];
// Yerler Supabase'den yüklenir — loadPlaces() ile"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: Demo yerler kaldırıldı, places boş başlıyor")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── PATCH 2: selectCity() — location bar güncelleme düzelt ────────────────
old2 = """let currentCity = 'Seoul';
function selectCity(name, country, flag) {
  currentCity = name;
  const dot = document.getElementById('location-dot');
  const text = document.getElementById('location-text');
  dot.style.background = '#10b981';
  text.textContent = flag + ' ' + name + ', ' + country;
  const addSub = document.getElementById('add-sub');
  if (addSub) addSub.textContent = name + ' · ' + (lang==='tr'?'Deneyimini paylaş':'Share your experience');
  // Para birimini güncelle
  currentCurrency = getCurrencyForCity(name);
  updateCurrencyBadge(name);
  // Şehir bazlı yerleri Supabase'den yükle
  currentCity = name;
  loadPlaces(name);
  goTo('screen-home');
}"""

new2 = """let currentCity = 'Seoul';
function selectCity(name, country, flag) {
  currentCity = name;
  const dot = document.getElementById('location-dot');
  const text = document.getElementById('location-text');
  if (dot) dot.style.background = '#10b981';
  if (text) text.textContent = flag + ' ' + name + ', ' + country;
  const addSub = document.getElementById('add-sub');
  if (addSub) addSub.textContent = name + ' · ' + (lang==='tr'?'Deneyimini paylaş':'Share your experience');
  currentCurrency = getCurrencyForCity(name);
  updateCurrencyBadge(name);
  loadPlaces(name);
  goTo('screen-home');
}"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: selectCity() location bar düzeltildi")
else:
    # Alternatif — currentCity çift yazılmış olabilir
    old2b = """function selectCity(name, country, flag) {
  currentCity = name;
  const dot = document.getElementById('location-dot');
  const text = document.getElementById('location-text');
  dot.style.background = '#10b981';
  text.textContent = flag + ' ' + name + ', ' + country;
  const addSub = document.getElementById('add-sub');
  if (addSub) addSub.textContent = name + ' · ' + (lang==='tr'?'Deneyimini paylaş':'Share your experience');
  // Para birimini güncelle
  currentCurrency = getCurrencyForCity(name);
  updateCurrencyBadge(name);
  // Şehir bazlı yerleri Supabase'den yükle
  currentCity = name;
  loadPlaces(name);
  goTo('screen-home');
}"""
    new2b = """function selectCity(name, country, flag) {
  currentCity = name;
  const dot = document.getElementById('location-dot');
  const text = document.getElementById('location-text');
  if (dot) dot.style.background = '#10b981';
  if (text) text.textContent = flag + ' ' + name + ', ' + country;
  const addSub = document.getElementById('add-sub');
  if (addSub) addSub.textContent = name + ' · ' + (lang==='tr'?'Deneyimini paylaş':'Share your experience');
  currentCurrency = getCurrencyForCity(name);
  updateCurrencyBadge(name);
  loadPlaces(name);
  goTo('screen-home');
}"""
    if old2b in html:
        html = html.replace(old2b, new2b)
        patches.append("✓ Patch 2b: selectCity() location bar düzeltildi")
    else:
        patches.append("✗ Patch 2 BULUNAMADI")

# ── PATCH 3: loadPlaces() — demoIds temizleme kısmını kaldır ─────────────
old3 = """    // Şehir değişince önceki Supabase yerlerini temizle (demo yerler kalır)
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
    }"""

new3 = """    // Şehir değişince tüm yerleri temizle, Supabase'den taze yükle
    places.length = 0;"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: loadPlaces() temizleme sadeleştirildi")
else:
    patches.append("✗ Patch 3 BULUNAMADI")

# ── PATCH 4: Init — loadPlaces Seoul ile başlasın ─────────────────────────
old4 = """renderCards();
renderSubCats();
updateCurrencyBadge('Seoul');
// Supabase'den yerleri yükle
loadPlaces();"""

new4 = """renderCards();
renderSubCats();
updateCurrencyBadge('Seoul');
// Supabase'den Seoul yerlerini yükle
loadPlaces('Seoul');"""

if old4 in html:
    html = html.replace(old4, new4)
    patches.append("✓ Patch 4: Init Seoul ile başlıyor")
else:
    patches.append("✗ Patch 4 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide Patch 4 Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup4', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"\n✅ {applied} patch uygulandı!")
    print("📦 Yedek: index.html.backup4")
else:
    print("\n⚠ Değişiklik yapılmadı")

print("="*50 + "\n")
