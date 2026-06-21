#!/usr/bin/env python3
# CrewGuide cleanup.py — Klasör temizliği
# patch*.py, fix_*.py dosyalarını patches_archive/ klasörüne taşır
# index.html.backup* dosyalarını backups/ klasörüne taşır
# Kullanım: python cleanup.py

import os
import shutil
import glob

def main():
    archive_dir = 'patches_archive'
    backup_dir = 'backups'

    os.makedirs(archive_dir, exist_ok=True)
    os.makedirs(backup_dir, exist_ok=True)

    moved_patches = []
    moved_backups = []
    skipped = []

    # Patch ve fix dosyalarını taşı
    patterns = ['patch*.py', 'fix_*.py', 'fix*.py']
    seen = set()
    for pattern in patterns:
        for f in glob.glob(pattern):
            if f in seen or f == 'cleanup.py':
                continue
            seen.add(f)
            dest = os.path.join(archive_dir, f)
            if os.path.exists(dest):
                skipped.append(f)
                continue
            shutil.move(f, dest)
            moved_patches.append(f)

    # Backup dosyalarını taşı
    for f in glob.glob('index.html.backup*'):
        dest = os.path.join(backup_dir, f)
        if os.path.exists(dest):
            skipped.append(f)
            continue
        shutil.move(f, dest)
        moved_backups.append(f)

    # Sonuç raporu
    print(f"\n{'='*55}")
    print("CrewGuide Klasör Temizliği")
    print('='*55)
    print(f"\n📦 {len(moved_patches)} patch dosyası → {archive_dir}/")
    for f in sorted(moved_patches):
        print(f"   {f}")

    print(f"\n💾 {len(moved_backups)} backup dosyası → {backup_dir}/")
    for f in sorted(moved_backups):
        print(f"   {f}")

    if skipped:
        print(f"\n⚠️  {len(skipped)} dosya zaten hedefte var, atlandı:")
        for f in sorted(skipped):
            print(f"   {f}")

    print(f"\n✅ Temizlik tamamlandı!")
    print(f"\nKalan ana dizin dosyaları:")
    for f in sorted(os.listdir('.')):
        if os.path.isfile(f) and f != 'cleanup.py':
            print(f"   {f}")
    print('='*55 + '\n')

    print("Not: index.html ve sw.js dokunulmadı, deploy.py çalışmaya devam eder.")
    print("Git'e commit etmek istersen:")
    print('  git add -A')
    print('  git commit -m "chore: klasör temizliği - patch ve backup dosyaları arşivlendi"')
    print('  git push')

if __name__ == '__main__':
    main()
