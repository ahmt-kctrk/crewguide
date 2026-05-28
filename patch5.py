#!/usr/bin/env python3
# CrewGuide patch5.py - Davet kodu input düzeltmesi

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 1: Davet kodu HTML — görsel kutular yerine gerçek input ──────────
old1 = """      <div class="code-entry">
        <div class="field-label" id="invite-code-label">DAVET KODU</div>
        <div class="code-boxes">
          <div class="code-box filled">C</div>
          <div class="code-box filled">R</div>
          <div class="code-box filled">W</div>
          <div class="code-box filled">-</div>
          <div class="code-box filled">X</div>
          <div class="code-box filled">7</div>
          <div class="code-box filled">K</div>
        </div>
        <div class="code-hint" id="invite-hint">7 haneli davet kodu · Büyük/küçük harf duyarsız</div>
      </div>"""

new1 = """      <div class="code-entry">
        <div class="field-label" id="invite-code-label">DAVET KODU</div>
        <input
          class="field-input"
          type="text"
          id="invite-code-input"
          placeholder="CRW-XXXXX"
          maxlength="10"
          autocomplete="off"
          autocapitalize="characters"
          style="text-align:center;font-family:'Syne',sans-serif;font-size:22px;font-weight:700;letter-spacing:4px;"
        >
        <div class="code-hint" id="invite-hint">7 haneli davet kodu · Büyük/küçük harf duyarsız</div>
      </div>"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: Davet kodu input eklendi")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ── PATCH 2: verifyInviteCode() — input'tan kodu al ───────────────────────
old2 = """async function verifyInviteCode() {
  const boxes = document.querySelectorAll('.code-box');
  const code = Array.from(boxes).map(b => b.textContent.trim()).join('').replace(/\\s/g,'');
  
  // Simüle edilmiş kod input — gerçek input olmadığı için sabit kodu al
  const inputCode = 'CRW-X7K'; // Şimdilik sabit, ilerleyen adımda gerçek input eklenecek"""

new2 = """async function verifyInviteCode() {
  const inputEl = document.getElementById('invite-code-input');
  const inputCode = inputEl ? inputEl.value.trim().toUpperCase() : '';
  
  if (!inputCode) {
    showToast(lang==='tr' ? 'Davet kodu gir!' : 'Enter invite code!');
    return;
  }"""

if old2 in html:
    html = html.replace(old2, new2)
    patches.append("✓ Patch 2: verifyInviteCode() gerçek input'tan okuyor")
else:
    patches.append("✗ Patch 2 BULUNAMADI")

# ── PATCH 3: "Kodum yok" butonu ────────────────────────────────────────────
old3 = """      <button class="btn-ghost" id="btn-no-code">Kodum yok, nasıl alabilirim?</button>"""

new3 = """      <button class="btn-ghost" id="btn-no-code" onclick="showToast(lang==='tr'?'Bir ekip arkadaşından davet kodu iste.':'Ask a colleague for an invite code.')">Kodum yok, nasıl alabilirim?</button>"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: Kodum yok butonu çalışıyor")
else:
    patches.append("✗ Patch 3 BULUNAMADI")

# ── SONUÇ ─────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CrewGuide Patch 5 Sonuçları")
print("="*50)
for p in patches:
    print(p)

if html != original:
    with open('index.html.backup5', 'w', encoding='utf-8') as f:
        f.write(original)
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    applied = len([p for p in patches if p.startswith("✓")])
    print(f"\n✅ {applied} patch uygulandı!")
    print("📦 Yedek: index.html.backup5")
else:
    print("\n⚠ Değişiklik yapılmadı")

print("="*50 + "\n")
