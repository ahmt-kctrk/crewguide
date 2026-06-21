#!/usr/bin/env python3
# CrewGuide patch27b.py — Syntax hatası düzeltmesi
# confirm() içindeki tek tırnak sorunu + Patch 2 ve 6 eksikleri

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
# PATCH 1 — disableMyAccount: tek tırnak → çift tırnak
# ══════════════════════════════════════════════════════════════════════════════
old1 = """  const confirmed = confirm(
    lang === 'tr'
      ? 'Hesabın devre dışı bırakılacak. Tekrar giriş yapamayacaksın.\\nDevam etmek istiyor musun?'
      : 'Your account will be disabled. You will not be able to sign in again.\\nContinue?'
  );"""

new1 = """  const confirmed = confirm(
    lang === 'tr'
      ? "Hesabın devre dışı bırakılacak. Tekrar giriş yapamayacaksın.\\nDevam etmek istiyor musun?"
      : "Your account will be disabled. You will not be able to sign in again.\\nContinue?"
  );"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: disableMyAccount syntax düzeltildi")
else:
    # Windows satır sonu ile dene
    old1b = old1.replace('\n', '\r\n')
    if old1b in html:
        html = html.replace(old1b, new1)
        patches.append("✓ Patch 1: disableMyAccount syntax düzeltildi (CRLF)")
    else:
        patches.append("✗ Patch 1 BULUNAMADI — manuel bak")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 2 — renderAdminInvites: Sil butonu (önceki patch2 bulunamadı)
# Mevcut "+ Kod Ver" butonunu bul ve Sil butonunu yanına ekle
# ══════════════════════════════════════════════════════════════════════════════
old2 = """          <button class="invite-add-btn" onclick="adminAddInviteCode('${u.id}', '${(u.username||'').replace(/'/g,"\\'")}')" >+ Kod Ver</button>"""

new2 = """          <div style="display:flex;gap:4px;align-items:center;">
            <button class="invite-add-btn" onclick="adminAddInviteCode('${u.id}', '${(u.username||'').replace(/'/g,"\\'")}')">+ Kod Ver</button>
            ${u.is_disabled
              ? `<button class="invite-delete-btn" onclick="adminEnableUser('${u.id}','${(u.username||'').replace(/'/g,"\\'")}')">✓ Aktif Et</button>`
              : `<button class="invite-delete-btn" onclick="adminDeleteUser('${u.id}','${(u.username||'').replace(/'/g,"\\'")}')">🗑 Sil</button>`
            }
          </div>"""

# Mevcut butonu farklı formatlarda ara
import re
pattern = r"""<button class="invite-add-btn" onclick="adminAddInviteCode\('\$\{u\.id\}', '\$\{\(u\.username\|\|''\)\.replace\(/'/g,.*?\)}'.*?\)">(\+\s*Kod Ver)</button>"""
match = re.search(pattern, html, re.DOTALL)
if match:
    old_btn = match.group(0)
    new_btn = """<div style="display:flex;gap:4px;align-items:center;">
            <button class="invite-add-btn" onclick="adminAddInviteCode('${u.id}', '${(u.username||'').replace(/'/g,"\\'")}')">+ Kod Ver</button>
            ${u.is_disabled
              ? `<button class="invite-delete-btn" onclick="adminEnableUser('${u.id}','${(u.username||'').replace(/'/g,"\\'")}')">✓ Aktif Et</button>`
              : `<button class="invite-delete-btn" onclick="adminDeleteUser('${u.id}','${(u.username||'').replace(/'/g,"\\'")}')">🗑 Sil</button>`
            }
          </div>"""
    html = html.replace(old_btn, new_btn)
    patches.append("✓ Patch 2: Sil butonu eklendi")
else:
    patches.append("✗ Patch 2 BULUNAMADI — manuel eklenecek")

# ══════════════════════════════════════════════════════════════════════════════
# PATCH 3 — Profil ekranına "Hesabımı Devre Dışı Bırak" butonu
# ══════════════════════════════════════════════════════════════════════════════
# Çıkış yap butonunu bul
sign_out_patterns = [
    'onclick="signOut()" style="width:100%;margin-top:8px;"',
    "onclick=\"signOut()\" style=\"width:100%;margin-top:8px;\"",
]

disable_btn = '<button class="btn-outline" onclick="disableMyAccount()" style="width:100%;margin-top:8px;border-color:#fca5a5;color:#991b1b;">⚠️ Hesabımı Devre Dışı Bırak</button>\n'

if 'disableMyAccount()' not in html:
    for pat in sign_out_patterns:
        if pat in html:
            idx = html.find(pat)
            # Butonun başına git
            start = html.rfind('<button', 0, idx)
            if start != -1:
                html = html[:start] + disable_btn + '          ' + html[start:]
                patches.append("✓ Patch 3: Profil devre dışı butonu eklendi")
                break
    else:
        patches.append("✗ Patch 3 — signOut butonu bulunamadı")
else:
    patches.append("✓ Patch 3: Zaten mevcut")

# ══════════════════════════════════════════════════════════════════════════════
# Kaydet
# ══════════════════════════════════════════════════════════════════════════════
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*55}")
    print("CrewGuide patch27b — Syntax + eksik patch düzeltmesi")
    print('='*55)
    for p in patches:
        print(f"  {p}")
    print(f"""
  python deploy.py "patch27b: syntax fix"
{'='*55}
""")
else:
    print("\n⚠️  Değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
