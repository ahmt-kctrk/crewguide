#!/usr/bin/env python3
# CrewGuide patch12.py - subscribePush yeni subscription oluşturur

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: subscribePush() — yeni subscription oluştur ─────────────────
old1 = """async function subscribePush() {
  if (!('PushManager' in window)) return;
  if (!navigator.serviceWorker.controller) return;
  try {
    const reg = await navigator.serviceWorker.ready;
    // Mevcut subscription varsa kullan
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      // Yeni subscription oluştur
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
      });
      console.log('[Push] Yeni subscription oluşturuldu');
    }
    await savePushSubscription(sub);
  } catch(e) {
    console.warn('[Push subscribe]', e);
  }
}"""

new1 = """const VAPID_PUBLIC_KEY = 'BAu2ytkOGAbktyX0MOKqotlIdwaHPgfuDHgV18pIMyLkLm1eFPLxzFwmhUWEzXD0kmxTX65-HDwtuhJk1Gpr-Cs';

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

async function subscribePush() {
  if (!('PushManager' in window)) return;
  try {
    const reg = await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
      });
      console.log('[Push] Yeni subscription oluşturuldu');
    }
    await savePushSubscription(sub);
  } catch(e) {
    console.warn('[Push subscribe]', e);
  }
}"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: subscribePush() VAPID key ile güncellendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide Patch 12 Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup12', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"\n✅ {applied} patch uygulandı!")
    print("📦 Yedek: index.html.backup12")
else:
    print("\n⚠ Değişiklik yapılmadı")

print("="*50 + "\n")
