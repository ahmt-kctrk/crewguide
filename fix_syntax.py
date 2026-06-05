#!/usr/bin/env python3
# Syntax hatası düzeltmesi — disableMyAccount confirm string

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Sorunlu blok — satır sonu içeren string
bad = (
    "      ? 'Hesabın devre dışı bırakılacak. Tekrar giriş yapamayacaksın.\n"
    "Devam etmek istiyor musun?'\n"
    "      : 'Your account will be disabled. You will not be able to sign in again.\n"
    "Continue?'\n"
    "  );"
)

good = (
    '      ? "Hesabın devre dışı bırakılacak. Devam etmek istiyor musun?"\n'
    '      : "Your account will be disabled. Continue?"\n'
    "  );"
)

if bad in html:
    html = html.replace(bad, good)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✓ Düzeltildi")
else:
    print("✗ Bulunamadı")
