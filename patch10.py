#!/usr/bin/env python3
# CrewGuide patch10.py - push_subscriptions JSONB formatı düzeltmesi

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: savePushSubscription() — JSONB formatında kaydet ────────────
old1 = """async function savePushSubscription(sub) {
  if (!currentUser) return;
  try {
    const subJson = sub.toJSON();
    await sbFetch('push_subscriptions', {
      method: 'POST',
      prefer: 'return=minimal',
      body: JSON.stringify({
        user_id: currentUser.id,
        endpoint: subJson.endpoint,
        p256dh: subJson.keys?.p256dh,
        auth: subJson.keys?.auth,
        city: currentCity || 'Seoul'
      })
    });
    console.log('[Push] Subscription kaydedildi');
  } catch(e) {
    console.warn('[Push save]', e);
  }
}"""

new1 = """async function savePushSubscription(sub) {
  if (!currentUser) return;
  try {
    const subJson = sub.toJSON();
    // Edge Function subscription kolonunu JSONB olarak bekliyor
    await sbFetch('push_subscriptions', {
      method: 'POST',
      prefer: 'return=minimal',
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
    console.log('[Push] Subscription kaydedildi');
  } catch(e) {
    console.warn('[Push save]', e);
  }
}"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: savePushSubscription() JSONB formatı düzeltildi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide Patch 10 Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup10', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"\n✅ {applied} patch uygulandı!")
    print("📦 Yedek: index.html.backup10")
else:
    print("\n⚠ Değişiklik yapılmadı")

print("="*50 + "\n")
