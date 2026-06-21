#!/usr/bin/env python3
# CrewGuide patch25.py — Kayıt çakışma hatası düzeltmesi
# Trigger + uygulama aynı anda profiles'a yazıyor → ON CONFLICT ile çöz
# Kullanım: python patch25.py

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
# PATCH 1 — Profil insert: Prefer: resolution=merge-duplicates ekle
# Trigger önce yazsa bile uygulama üzerine yazar, hata vermez
# ══════════════════════════════════════════════════════════════════════════════
old1 = """    // 2. Profil oluştur (kendi kodu — tek ana kod)
    const newInviteCode = 'CRW-' + Math.random().toString(36).substring(2,5).toUpperCase();
    await fetch(SUPABASE_URL + '/rest/v1/profiles', {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + accessToken,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify({
        id: userId,
        username,
        invite_code: newInviteCode,
        invited_by: inviteCode
      })
    });"""

new1 = """    // 2. Profil oluştur (kendi kodu — tek ana kod)
    // Prefer: resolution=merge-duplicates → trigger önce yazsa çakışma olmaz
    const newInviteCode = 'CRW-' + Math.random().toString(36).substring(2,5).toUpperCase();
    const profileRes = await fetch(SUPABASE_URL + '/rest/v1/profiles', {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + accessToken,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal,resolution=merge-duplicates'
      },
      body: JSON.stringify({
        id: userId,
        username,
        invite_code: newInviteCode,
        invited_by: inviteCode
      })
    });
    if (!profileRes.ok) {
      const errText = await profileRes.text();
      console.warn('[createAccount] Profil hatası:', errText);
      // 409 Conflict dışındaki hataları fırlat
      if (profileRes.status !== 409) throw new Error('Profil oluşturulamadı: ' + errText);
    }"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: Profil insert çakışma düzeltmesi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# Kaydet
# ══════════════════════════════════════════════════════════════════════════════
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*55}")
    print("CrewGuide patch25 — Kayıt çakışma düzeltmesi")
    print('='*55)
    for p in patches:
        print(f"  {p}")
    print(f"""
── Sonraki adımlar ─────────────────────────────────────
  1. python deploy.py "patch25: kayıt çakışma düzeltmesi"
  2. Yeni kullanıcı kaydı test et — hata mesajı çıkmamalı
{'='*55}
""")
else:
    print("\n⚠️  Değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
