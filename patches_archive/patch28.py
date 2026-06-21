#!/usr/bin/env python3
# CrewGuide patch28.py — Silinmiş kullanıcı otomatik çıkış
# loadProfile: profil bulunamazsa signOut çağır

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
# PATCH 1 — loadProfile: profil yoksa otomatik çıkış
# ══════════════════════════════════════════════════════════════════════════════
old1 = """    const data = await res.json();
    if (data && data[0]) {
      currentProfile = data[0];
      localStorage.setItem('sb_profile', JSON.stringify(currentProfile));
    }"""

new1 = """    const data = await res.json();
    if (data && data[0]) {
      currentProfile = data[0];
      localStorage.setItem('sb_profile', JSON.stringify(currentProfile));
      // Hesap devre dışıysa çıkış yap
      if (currentProfile.is_disabled) {
        console.warn('[loadProfile] Hesap devre dışı — çıkış yapılıyor');
        showToast(lang === 'tr' ? 'Hesabın devre dışı bırakılmış.' : 'Your account has been disabled.');
        setTimeout(() => signOut(), 1500);
        return;
      }
    } else {
      // Profil bulunamadı — hesap silinmiş, çıkış yap
      console.warn('[loadProfile] Profil bulunamadı — çıkış yapılıyor');
      localStorage.removeItem('sb_profile');
      localStorage.removeItem('sb_access_token');
      localStorage.removeItem('sb_refresh_token');
      localStorage.removeItem('sb_user');
      sessionStorage.clear();
      currentUser = null;
      currentProfile = null;
      showToast(lang === 'tr' ? 'Oturum geçersiz.' : 'Session invalid.');
      setTimeout(() => goTo('screen-splash'), 1000);
      return;
    }"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: Profil bulunamazsa otomatik çıkış")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# Kaydet
# ══════════════════════════════════════════════════════════════════════════════
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*55}")
    print("CrewGuide patch28 — Silinmiş kullanıcı otomatik çıkış")
    print('='*55)
    for p in patches:
        print(f"  {p}")
    print(f"""
  python deploy.py "patch28: silinmiş kullanıcı otomatik çıkış"
{'='*55}
""")
else:
    print("\n⚠️  Değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
