#!/usr/bin/env python3
# CrewGuide patch11.py - subscribePush fonksiyonu + add-sub düzeltmesi

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: subscribePush + savePushSubscription fonksiyonları ekle ──────
push_funcs = """
// ── PUSH SUBSCRIPTION ────────────────────────────────────────────────────────
async function subscribePush() {
  if (!('PushManager' in window)) return;
  if (!navigator.serviceWorker.controller) return;
  try {
    const reg = await navigator.serviceWorker.ready;
    const existing = await reg.pushManager.getSubscription();
    if (existing) {
      await savePushSubscription(existing);
      return;
    }
  } catch(e) {
    console.warn('[Push subscribe]', e);
  }
}

async function savePushSubscription(sub) {
  if (!currentUser) return;
  try {
    const subJson = sub.toJSON();
    const token = sessionStorage.getItem('sb_access_token');
    const res = await fetch(SUPABASE_URL + '/rest/v1/push_subscriptions', {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + (token || SUPABASE_KEY),
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify({
        user_id: currentUser.id,
        subscription: {
          endpoint: subJson.endpoint,
          keys: {
            p256dh: subJson.keys?.p256dh,
            auth: subJson.keys?.auth
          }
        },
        city: currentCity || 'Seoul'
      })
    });
    if (res.ok) {
      console.log('[Push] Subscription kaydedildi');
    } else {
      console.warn('[Push save]', await res.text());
    }
  } catch(e) {
    console.warn('[Push save]', e);
  }
}

"""

if 'async function subscribePush' not in html:
    old1 = "function resetTheme() {"
    if old1 in html:
        html = html.replace(old1, push_funcs + old1, 1)
        patches.append("✓ Patch 1: subscribePush + savePushSubscription eklendi")
    else:
        patches.append("✗ Patch 1: resetTheme bulunamadı")
else:
    patches.append("⚠ Patch 1: subscribePush zaten var")

# ── PATCH 2: add-sub Seoul sabit yazısını düzelt ──────────────────────────
old2 = """      <div class="header-sub" id="add-sub">Seoul · Deneyimini paylaş</div>"""
new2 = """      <div class="header-sub" id="add-sub">· Deneyimini paylaş</div>"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: add-sub Seoul sabit yazısı kaldırıldı")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide Patch 11 Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup11', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"\n✅ {applied} patch uygulandı!")
    print("📦 Yedek: index.html.backup11")
else:
    print("\n⚠ Değişiklik yapılmadı")

print("="*50 + "\n")
