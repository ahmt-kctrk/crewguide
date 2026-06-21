#!/usr/bin/env python3
# CrewGuide patch29.py — Kayıt akışı: metadata ile trigger
# signUp'a user_metadata göm, profil oluşturma kodunu kaldır
# Kullanım: python patch29.py

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
# PATCH 1 — signUp'a user_metadata ekle
# ══════════════════════════════════════════════════════════════════════════════
old1 = """    // 1. Supabase Auth'da kayıt
    const authData = await authFetch('signup', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    const userId = authData.user?.id;
    const accessToken = authData.access_token;
    if (!userId) throw new Error('User ID alınamadı');

    // 2. Profil oluştur (kendi kodu — tek ana kod)
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
    }

    // 3. Kullanıcıya 3 adet davet kodu üret
    const inviteCodes = [];
    for (let i = 0; i < 3; i++) {
      const code = 'CRW-' + Math.random().toString(36).substring(2,5).toUpperCase() + Math.random().toString(36).substring(2,4).toUpperCase();
      inviteCodes.push({ code, created_by: userId });
    }
    await sbFetch('invite_codes', {
      method: 'POST',
      prefer: 'return=minimal',
      body: JSON.stringify(inviteCodes)
    });

    // 4. Kullanılan davet kodunu işaretle (master kod için atlıyoruz)
    const isMaster = sessionStorage.getItem('isMasterInvite') === 'true';
    sessionStorage.removeItem('isMasterInvite');
    if (!isMaster) await sbFetch(`invite_codes?code=eq.${encodeURIComponent(inviteCode)}`, {
      method: 'PATCH',
      body: JSON.stringify({ used_by: userId, used_at: new Date().toISOString() })
    });

    // 5. Session kaydet
    sessionStorage.setItem('sb_access_token', accessToken);"""

new1 = """    // 1. Supabase Auth'da kayıt — metadata ile trigger profili oluşturur
    const newInviteCode = 'CRW-' + Math.random().toString(36).substring(2,5).toUpperCase();
    const isMaster = sessionStorage.getItem('isMasterInvite') === 'true';

    const authData = await authFetch('signup', {
      method: 'POST',
      body: JSON.stringify({
        email,
        password,
        data: {
          username,
          invite_code: newInviteCode,
          invited_by: inviteCode,
        }
      })
    });

    const userId = authData.user?.id;
    const accessToken = authData.access_token;

    // Email doğrulama gerekiyorsa access_token gelmez — bu normal
    if (!userId) throw new Error('User ID alınamadı');

    // 2. Davet kodunu kullanıldı işaretle (arka planda — hata olsa devam et)
    try {
      sessionStorage.removeItem('isMasterInvite');
      if (!isMaster) {
        await fetch(`${SUPABASE_URL}/rest/v1/invite_codes?code=eq.${encodeURIComponent(inviteCode)}`, {
          method: 'PATCH',
          headers: {
            'apikey': SUPABASE_KEY,
            'Authorization': 'Bearer ' + SUPABASE_KEY,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
          },
          body: JSON.stringify({ used_by: userId, used_at: new Date().toISOString() })
        });
      }
    } catch(e) {
      console.warn('[createAccount] Davet kodu işaretlenemedi:', e);
    }

    // 3. Email doğrulama gerekiyorsa — teşekkür ekranı göster
    if (!accessToken) {
      showToast(lang === 'tr'
        ? '📧 Doğrulama emaili gönderildi! Emailini kontrol et.'
        : '📧 Verification email sent! Check your inbox.');
      btn.textContent = lang === 'tr' ? 'Email gönderildi ✓' : 'Email sent ✓';
      btn.disabled = false;

      // Giriş ekranına yönlendir
      setTimeout(() => goTo('screen-login'), 2500);
      return;
    }

    // 4. Email doğrulama kapalıysa direkt session kaydet
    sessionStorage.setItem('sb_access_token', accessToken);"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: signUp metadata + email doğrulama akışı")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# Kaydet
# ══════════════════════════════════════════════════════════════════════════════
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*58}")
    print("CrewGuide patch29 — Kayıt akışı: metadata trigger")
    print('='*58)
    for p in patches:
        print(f"  {p}")
    print(f"""
  python deploy.py "patch29: kayıt metadata trigger"

  Yeni akış:
  1. Kullanıcı formu doldurup kayıt olur
  2. Supabase email gönderir
  3. "Doğrulama emaili gönderildi" mesajı + giriş ekranına yönlenir
  4. Trigger username/invite_code/invited_by ile profili oluşturur
  5. Kullanıcı emaili doğrulayıp giriş yapar — profil hazır
{'='*58}
""")
else:
    print("\n⚠️  Değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
