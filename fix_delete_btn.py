#!/usr/bin/env python3
# Sil butonu tırnak hatası düzeltmesi

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old = """? `<button class="invite-delete-btn" onclick="adminEnableUser('${u.id}','${(u.username||'').replace(/'/g,"\\'")}')">✓ Aktif Et</button>`
              : `<button class="invite-delete-btn" onclick="adminDeleteUser('${u.id}','${(u.username||'').replace(/'/g,"\\'")}')">🗑 Sil</button>`"""

new = """? `<button class="invite-delete-btn" onclick="adminEnableUser('${u.id}', this)">✓ Aktif Et</button>`
              : `<button class="invite-delete-btn" onclick="adminDeleteUser('${u.id}', this)">🗑 Sil</button>`"""

if old in html:
    html = html.replace(old, new)
    print("✓ Düzeltildi")
else:
    print("✗ Bulunamadı — farklı formatta aranıyor...")
    # CRLF ile dene
    old2 = old.replace('\n', '\r\n')
    if old2 in html:
        html = html.replace(old2, new)
        print("✓ CRLF ile düzeltildi")
    else:
        print("✗ Hâlâ bulunamadı")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# adminDeleteUser ve adminEnableUser: username parametresini data-attribute'tan al
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

old2 = "async function adminDeleteUser(userId, username) {\n  if (!isAdmin()) return;\n  const confirmed = confirm(`\"${username}\" kullanıcısı kalıcı olarak silinecek!"
new2 = "async function adminDeleteUser(userId, btn) {\n  if (!isAdmin()) return;\n  const username = btn?.closest('.invite-user-row')?.querySelector('.invite-user-name')?.textContent?.trim()?.split(' ')[0] || userId;\n  const confirmed = confirm(`\"${username}\" kullanıcısı kalıcı olarak silinecek!"

if old2 in html:
    html = html.replace(old2, new2)
    print("✓ adminDeleteUser güncellendi")
else:
    print("✗ adminDeleteUser bulunamadı")

old3 = "async function adminEnableUser(userId, username) {\n  if (!isAdmin()) return;\n  const confirmed = confirm(`\"${username}\" hesabı yeniden aktif edilsin mi?`);"
new3 = "async function adminEnableUser(userId, btn) {\n  if (!isAdmin()) return;\n  const username = btn?.closest('.invite-user-row')?.querySelector('.invite-user-name')?.textContent?.trim()?.split(' ')[0] || userId;\n  const confirmed = confirm(`\"${username}\" hesabı yeniden aktif edilsin mi?`);"

if old3 in html:
    html = html.replace(old3, new3)
    print("✓ adminEnableUser güncellendi")
else:
    print("✗ adminEnableUser bulunamadı")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Tamamlandı")
