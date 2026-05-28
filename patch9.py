#!/usr/bin/env python3
# CrewGuide patch9.py - Normal kullanıcı kendi yerini silebilsin

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: openDetail() — admin ve owner için silme butonu göster ───────
old1 = """  // Admin butonunu göster/gizle
  const adminActions = document.getElementById('admin-actions');
  if (adminActions) adminActions.style.display = isAdmin() ? 'block' : 'none';"""

new1 = """  // Silme butonunu göster/gizle — admin veya yerin sahibi
  const adminActions = document.getElementById('admin-actions');
  const isOwner = currentUser && p.userId && currentUser.id === p.userId;
  if (adminActions) adminActions.style.display = (isAdmin() || isOwner) ? 'block' : 'none';"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: openDetail() owner kontrolü eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── PATCH 2: Admin buton metnini güncelle ─────────────────────────────────
old2 = """          🗑 Yeri Kaldır (Admin)"""

new2 = """          🗑 <span id="delete-place-label">Yeri Kaldır</span>"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: Buton metni güncellendi")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ── PATCH 3: adminDeletePlace() — owner da silebilsin ────────────────────
old3 = """async function adminDeletePlace() {
  if (!isAdmin()) { showToast('Yetkisiz işlem!'); return; }"""

new3 = """async function adminDeletePlace() {
  const p = places.find(x => x.id === currentDetailId);
  const isOwner = currentUser && p && p.userId && currentUser.id === p.userId;
  if (!isAdmin() && !isOwner) { showToast(lang==='tr'?'Yetkisiz işlem!':'Unauthorized!'); return; }"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: adminDeletePlace() owner kontrolü eklendi")
else:
    patches.append("✗ Patch 3 BULUNAMADI")

# ── PATCH 4: adminDeletePlace() — ikinci p tanımını kaldır ───────────────
old4 = """  const p = places.find(x => x.id === currentDetailId);
  if (!p) return;

  const confirmed = confirm("""

new4 = """  if (!p) return;

  const confirmed = confirm("""

if old4 in html:
    html = html.replace(old4, new4, 1)
    patches.append("✓ Patch 4: Duplicate p tanımı kaldırıldı")
else:
    patches.append("✗ Patch 4 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide Patch 9 Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup9', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"\n✅ {applied} patch uygulandı!")
    print("📦 Yedek: index.html.backup9")
else:
    print("\n⚠ Değişiklik yapılmadı")

print("="*50 + "\n")
