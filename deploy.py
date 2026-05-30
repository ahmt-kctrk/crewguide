#!/usr/bin/env python3
# CrewGuide deploy.py
# sw.js cache versiyonunu otomatik günceller ve git push yapar
# Kullanım: python deploy.py "commit mesajı"

import sys
import os
import re
import subprocess
from datetime import datetime

def run(cmd, check=True):
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print(f"    {result.stdout.strip()}")
    if result.stderr.strip() and result.returncode != 0:
        print(f"    ERR: {result.stderr.strip()}")
    if check and result.returncode != 0:
        print(f"\n❌ Komut başarısız: {cmd}")
        sys.exit(1)
    return result

def main():
    # Commit mesajı
    if len(sys.argv) > 1:
        commit_msg = " ".join(sys.argv[1:])
    else:
        commit_msg = f"update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    print("\n" + "="*50)
    print("CrewGuide Deploy")
    print("="*50)

    # sw.js dosyasını bul
    sw_path = "sw.js"
    if not os.path.exists(sw_path):
        print("❌ sw.js bulunamadı! Bu scripti proje klasöründe çalıştır.")
        sys.exit(1)

    # Timestamp oluştur
    ts = datetime.now().strftime("%Y%m%d%H%M")

    # sw.js'i güncelle
    with open(sw_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Cache versiyonlarını güncelle
    updated = re.sub(
        r"const STATIC_CACHE = 'crewguide-static-[\w-]+'",
        f"const STATIC_CACHE = 'crewguide-static-{ts}'",
        content
    )
    updated = re.sub(
        r"const DYNAMIC_CACHE = 'crewguide-dynamic-[\w-]+'",
        f"const DYNAMIC_CACHE = 'crewguide-dynamic-{ts}'",
        updated
    )
    # BUILD timestamp güncelle
    updated = re.sub(
        r"// BUILD: \d+",
        f"// BUILD: {ts}",
        updated
    )
    if "// BUILD:" not in updated:
        updated = updated.replace(
            "// CrewGuide Service Worker",
            f"// CrewGuide Service Worker\n// BUILD: {ts}"
        )

    if updated == content:
        print("⚠️  sw.js'de değiştirilecek cache satırı bulunamadı")
        print("   sw.js'in doğru formatta olduğundan emin ol")
    else:
        with open(sw_path, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"✓ sw.js güncellendi (BUILD: {ts})")

    print(f"\n📦 Commit: {commit_msg}")

    # Git işlemleri
    print("\n─── Git ───────────────────────────────────")
    run("git add -A")
    run(f'git commit -m "{commit_msg}"')
    run("git push")

    print("\n✅ Deploy tamamlandı!")
    print(f"   BUILD: {ts}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
