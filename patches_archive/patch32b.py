#!/usr/bin/env python3
# CrewGuide patch32b — Eksik patch'leri uygula

import os, sys

fname = 'index.html'
if not os.path.exists(fname):
    print(f"HATA: {fname} bulunamadı.")
    sys.exit(1)

with open(fname, 'r', encoding='utf-8') as f:
    html = f.read()

original = html
patches = []

# ── PATCH 2: openDetail'e düzenle butonu görünürlük ──────────────────────────
old2 = "  if (adminActions) adminActions.style.display = (isAdmin() || isOwner) ? 'block' : 'none';\r\n  goTo('screen-detail');"
new2 = """  if (adminActions) adminActions.style.display = isAdmin() ? 'block' : 'none';

  // Düzenle butonu — yerin sahibi veya admin
  const editAction = document.getElementById('edit-place-action');
  if (editAction) {
    const canEdit = isAdmin() || (currentUser && p.userId === currentUser.id);
    editAction.style.display = canEdit ? 'block' : 'none';
  }
  goTo('screen-detail');"""

if old2.replace('\r\n', '\n') in html.replace('\r\n', '\n'):
    html = html.replace(
        "  if (adminActions) adminActions.style.display = (isAdmin() || isOwner) ? 'block' : 'none';\r\n  goTo('screen-detail');",
        new2
    )
    if "  if (adminActions) adminActions.style.display = (isAdmin() || isOwner) ? 'block' : 'none';\ngoTo" in html:
        pass
    patches.append("✓ Patch 2: Düzenle butonu görünürlük eklendi")
else:
    # LF dene
    old2b = "  if (adminActions) adminActions.style.display = (isAdmin() || isOwner) ? 'block' : 'none';\n  goTo('screen-detail');"
    if old2b in html:
        html = html.replace(old2b, new2)
        patches.append("✓ Patch 2 (LF): Düzenle butonu görünürlük eklendi")
    else:
        patches.append("✗ Patch 2 BULUNAMADI")

# ── PATCH 3: submitPlace edit modu ───────────────────────────────────────────
old3 = "  const placeId = 'place_' + Date.now();\r\n  const newPlace = {"
old3b = "  const placeId = 'place_' + Date.now();\n  const newPlace = {"
new3 = """  // Edit modu kontrolü
  const editMode = !!window._editingPlaceId;
  const placeId = editMode ? window._editingPlaceId : 'place_' + Date.now();

  const newPlace = {"""

if old3 in html:
    html = html.replace(old3, new3)
    patches.append("✓ Patch 3: Edit modu değişkeni eklendi")
elif old3b in html:
    html = html.replace(old3b, new3)
    patches.append("✓ Patch 3 (LF): Edit modu değişkeni eklendi")
else:
    patches.append("✗ Patch 3 BULUNAMADI")

# ── PATCH 4: submitPlace PATCH/POST ayrımı ───────────────────────────────────
old4 = "      await sbFetch('places', { method: 'POST', body: JSON.stringify(placePayload) });\r\n      sendPushForNewPlace"
old4b = "      await sbFetch('places', { method: 'POST', body: JSON.stringify(placePayload) });\n      sendPushForNewPlace"
new4 = """      if (editMode) {
        const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;
        await fetch(`${SUPABASE_URL}/rest/v1/places?id=eq.${placeId}`, {
          method: 'PATCH',
          headers: {
            'apikey': SUPABASE_KEY,
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
          },
          body: JSON.stringify(placePayload)
        });
      } else {
        await sbFetch('places', { method: 'POST', body: JSON.stringify(placePayload) });
        sendPushForNewPlace"""

if old4 in html:
    # Satırın devamını da bulmamız lazım
    idx = html.find(old4)
    # sendPushForNewPlace satırının sonunu bul
    end_idx = html.find('\n', idx + len(old4))
    old_full = html[idx:end_idx]
    push_call = old_full[len("      await sbFetch('places', { method: 'POST', body: JSON.stringify(placePayload) });\r\n      "):]
    new4_full = new4 + push_call + "\n      }"
    html = html[:idx] + new4_full + html[end_idx:]
    patches.append("✓ Patch 4: PATCH/POST ayrımı eklendi")
elif old4b in html:
    idx = html.find(old4b)
    end_idx = html.find('\n', idx + len(old4b))
    old_full = html[idx:end_idx]
    push_call = old_full[len("      await sbFetch('places', { method: 'POST', body: JSON.stringify(placePayload) });\n      "):]
    new4_full = new4 + push_call + "\n      }"
    html = html[:idx] + new4_full + html[end_idx:]
    patches.append("✓ Patch 4 (LF): PATCH/POST ayrımı eklendi")
else:
    patches.append("✗ Patch 4 BULUNAMADI")

# ── PATCH 5: submitPlace toast + yönlendirme ─────────────────────────────────
old5 = "    showToast(lang==='tr'?'Yer başarıyla eklendi! 🎉':'Place added successfully! 🎉');\r\n    // Yeni şehri dynamicCities'e ekle\r\n    addCityToDynamic(currentCity, currentCountry, currentFlag);\r\n    setTimeout(() => { goTo('screen-home'); renderCards(); }, 1000);\r\n  }\r\n}"
old5b = "    showToast(lang==='tr'?'Yer başarıyla eklendi! 🎉':'Place added successfully! 🎉');\n    // Yeni şehri dynamicCities'e ekle\n    addCityToDynamic(currentCity, currentCountry, currentFlag);\n    setTimeout(() => { goTo('screen-home'); renderCards(); }, 1000);\n  }\n}"

new5 = """    const successMsg = editMode
      ? (lang==='tr' ? 'Yer güncellendi! ✓' : 'Place updated! ✓')
      : (lang==='tr' ? 'Yer başarıyla eklendi! 🎉' : 'Place added successfully! 🎉');
    showToast(successMsg);
    if (!editMode) addCityToDynamic(currentCity, currentCountry, currentFlag);
    window._editingPlaceId = null;
    const addTitle = document.getElementById('add-title');
    const submitBtn = document.getElementById('btn-submit');
    if (addTitle) addTitle.textContent = lang==='tr' ? 'Yeni Yer Ekle' : 'Add Place';
    if (submitBtn) submitBtn.textContent = lang==='tr' ? 'Paylaş →' : 'Share →';
    setTimeout(() => { goTo('screen-home'); renderCards(); }, 1000);
  }
}"""

if old5 in html:
    html = html.replace(old5, new5)
    patches.append("✓ Patch 5: Toast + yönlendirme güncellendi")
elif old5b in html:
    html = html.replace(old5b, new5)
    patches.append("✓ Patch 5 (LF): Toast + yönlendirme güncellendi")
else:
    patches.append("✗ Patch 5 BULUNAMADI")

# ── Kaydet ───────────────────────────────────────────────────────────────────
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*55}")
    print("CrewGuide patch32b — Eksik patch'ler")
    print('='*55)
    for p in patches:
        print(f"  {p}")
    print("\n  python deploy.py \"patch32b: yer düzenleme tamamlandı\"")
    print('='*55)
else:
    print("\n⚠️  Değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
