#!/usr/bin/env python3
# CrewGuide patch30.py — Seoul default kaldır
# Yeni kullanıcıda profil gittiğim şehirler boş başlasın

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
# PATCH 1 — loadPlaces('Seoul') → loadPlaces() — şehir seçilmeden yükleme yapma
# ══════════════════════════════════════════════════════════════════════════════
old1 = "loadPlaces('Seoul');"
new1 = "// Başlangıçta şehir seçilmeden yükleme yapma — kullanıcı şehir seçince yüklenir\nif (currentCity && currentCity !== 'Seoul') loadPlaces(currentCity);"

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: loadPlaces Seoul default kaldırıldı")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 2 — currentCity başlangıç değerini null yap
# ══════════════════════════════════════════════════════════════════════════════
old2 = "let currentCity = 'Seoul';"
new2 = "let currentCity = localStorage.getItem('cg_last_city') || null;"

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: currentCity başlangıç değeri localStorage'dan")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 3 — selectCity: seçilen şehri localStorage'a kaydet
# ══════════════════════════════════════════════════════════════════════════════
old3 = """function selectCity(name, country, flag) {
  currentCity = name;
  // Ziyaret edilen şehre ekle
  addVisitedCity(name);"""

new3 = """function selectCity(name, country, flag) {
  currentCity = name;
  // Son şehri kaydet
  localStorage.setItem('cg_last_city', name);
  // Ziyaret edilen şehre ekle
  addVisitedCity(name);"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: selectCity son şehri kaydediyor")
else:
    patches.append("✗ Patch 3 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# Kaydet
# ══════════════════════════════════════════════════════════════════════════════
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*55}")
    print("CrewGuide patch30 — Seoul default kaldır")
    print('='*55)
    for p in patches:
        print(f"  {p}")
    print(f"""
  python deploy.py "patch30: Seoul default kaldır"

  Yeni davranış:
  - Yeni kullanıcı: profilde gittiğim şehirler boş
  - Şehir seçince localStorage'a kaydedilir
  - Sonraki açılışta son şehir hatırlanır
{'='*55}
""")
else:
    print("\n⚠️  Değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
