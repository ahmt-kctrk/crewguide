#!/usr/bin/env python3
# CrewGuide patch26.py — "Davet eden" gösterimi düzeltmesi
# invite_codes tablosundan code → created_by → username zinciri
# Kullanım: python patch26.py

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
# PATCH 1 — allAdminUsers map'ine invitedByUsername ekle
# inviteCodes zaten çekilmiş — code → created_by → profile username
# ══════════════════════════════════════════════════════════════════════════════
old1 = """    // Her profile'a kodlarını eşleştir
    allAdminUsers = profiles.map(p => ({
      ...p,
      codes: inviteCodes.filter(c => c.created_by === p.id)
    }));"""

new1 = """    // id → username hızlı lookup
    const idToUsername = {};
    profiles.forEach(p => { idToUsername[p.id] = p.username; });

    // Her profile'a kodlarını ve davet eden bilgisini eşleştir
    allAdminUsers = profiles.map(p => {
      // invited_by kodu invite_codes tablosunda kim tarafından oluşturulmuş?
      const usedCode = inviteCodes.find(c => c.code === p.invited_by);
      const invitedByUsername = usedCode?.created_by
        ? (idToUsername[usedCode.created_by] || 'Bilinmiyor')
        : (p.invited_by ? p.invited_by : null); // CRW-MASTER gibi hardcoded kodlar

      return {
        ...p,
        codes: inviteCodes.filter(c => c.created_by === p.id),
        invitedByUsername,
      };
    });"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: allAdminUsers'a invitedByUsername eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 2 — renderAdminInvites: invitedByUser yerine invitedByUsername kullan
# ══════════════════════════════════════════════════════════════════════════════
old2 = """    const invitedByUser = u.invited_by ? allAdminUsers.find(x => x.invite_code === u.invited_by) : null;"""

new2 = """    // invitedByUsername loadAdminInvites'ta hesaplandı
    const invitedByLabel = u.invitedByUsername || null;"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: renderAdminInvites invitedByUser kaldırıldı")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 3 — renderAdminInvites: gösterim satırını güncelle
# ══════════════════════════════════════════════════════════════════════════════
old3 = """              ${invitedByUser ? ` · Davet eden: <b>${invitedByUser.username}</b>` : ' · (Kurucu/Master)'}"""

new3 = """              ${invitedByLabel ? ` · Davet eden: <b>${invitedByLabel}</b>` : ''}"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: Davet eden gösterimi güncellendi")
else:
    patches.append("✗ Patch 3 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# Kaydet
# ══════════════════════════════════════════════════════════════════════════════
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*55}")
    print("CrewGuide patch26 — Davet eden gösterimi düzeltmesi")
    print('='*55)
    for p in patches:
        print(f"  {p}")
    print(f"""
── Sonraki adımlar ─────────────────────────────────────
  python deploy.py "patch26: davet eden gösterimi düzeltmesi"

  Beklenen sonuç:
  korecan   → Davet eden: (boş — kurucu)
  goreli    → Davet eden: korecan
  diğerleri → Davet eden: korecan (CRW-MASTER ile geldilerse)
{'='*55}
""")
else:
    print("\n⚠️  Değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
