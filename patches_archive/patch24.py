#!/usr/bin/env python3
# CrewGuide patch24.py — Çalışma saati: Supabase Edge Function proxy
# Google Places API artık Edge Function üzerinden çağrılır (CORS yok)
# Kullanım: python patch24.py

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
# PATCH 1 — fetchFromGoogle: tarayıcıdan Google'a değil, Edge Function'a git
# ══════════════════════════════════════════════════════════════════════════════
old1 = """async function fetchFromGoogle(p) {
  const badge = document.getElementById('hours-badge');
  if (!badge) return;

  // Loading göster
  badge.className = 'hours-badge loading';
  badge.style.display = 'flex';
  document.getElementById('hours-main').textContent = lang === 'tr' ? 'Saatler yükleniyor...' : 'Loading hours...';
  document.getElementById('hours-detail').textContent = '';
  const toggleBtn = document.getElementById('hours-toggle');
  if (toggleBtn) toggleBtn.style.display = 'none';

  try {
    // Step 1: Text Search ile place_id bul (zaten yoksa)
    let placeId = p.googlePlaceId;
    if (!placeId) {
      const searchQuery = encodeURIComponent(`${p.name} ${p.addr}`);
      const searchRes = await fetch(
        `https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input=${searchQuery}&inputtype=textquery&fields=place_id&key=${GOOGLE_PLACES_KEY}`,
        { mode: 'cors' }
      );
      const searchData = await searchRes.json();
      if (searchData.candidates && searchData.candidates[0]) {
        placeId = searchData.candidates[0].place_id;
        // Supabase'e kaydet
        saveGooglePlaceId(p.id, placeId);
        p.googlePlaceId = placeId;
      }
    }

    if (!placeId) {
      badge.style.display = 'none';
      return;
    }

    // Step 2: Place Details ile opening_hours çek
    const detailRes = await fetch(
      `https://maps.googleapis.com/maps/api/place/details/json?place_id=${placeId}&fields=opening_hours,utc_offset_minutes&key=${GOOGLE_PLACES_KEY}`,
      { mode: 'cors' }
    );
    const detailData = await detailRes.json();
    const oh = detailData.result?.opening_hours;

    if (!oh) {
      badge.style.display = 'none';
      return;
    }

    // Supabase'e kaydet
    saveOpeningHours(p.id, placeId, oh);
    p.openingHours = oh;

    const cacheKey = placeId || p.id;
    const result = parseGoogleHours(oh, cacheKey);
    hoursCache[cacheKey] = result;
    renderHoursBadge(result);

  } catch(e) {
    console.warn('[Hours] Google Places hatası:', e);
    badge.style.display = 'none';
  }
}"""

new1 = """async function fetchFromGoogle(p) {
  const badge = document.getElementById('hours-badge');
  if (!badge) return;

  // Loading göster
  badge.className = 'hours-badge loading';
  badge.style.display = 'flex';
  document.getElementById('hours-main').textContent = lang === 'tr' ? 'Saatler yükleniyor...' : 'Loading hours...';
  document.getElementById('hours-detail').textContent = '';
  const toggleBtn = document.getElementById('hours-toggle');
  if (toggleBtn) toggleBtn.style.display = 'none';

  try {
    // Edge Function üzerinden çağır (CORS sorunu yok, API key güvende)
    const token = sessionStorage.getItem('sb_access_token') || localStorage.getItem('sb_access_token') || SUPABASE_KEY;
    const res = await fetch(
      `${SUPABASE_URL}/functions/v1/places-hours`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token,
          'apikey': SUPABASE_KEY,
        },
        body: JSON.stringify({
          name: p.name,
          addr: p.addr,
          placeId: p.googlePlaceId || null,
        })
      }
    );

    if (!res.ok) throw new Error('Edge Function hata: ' + res.status);
    const data = await res.json();

    if (!data.found || !data.opening_hours) {
      console.log('[Hours] Yer bulunamadı veya saat yok:', p.name);
      badge.style.display = 'none';
      return;
    }

    const oh = data.opening_hours;
    const googlePlaceId = data.google_place_id;

    // Supabase'e kaydet (arka planda)
    saveOpeningHours(p.id, googlePlaceId, oh);
    p.openingHours = oh;
    p.googlePlaceId = googlePlaceId;

    const cacheKey = googlePlaceId || p.id;
    const result = parseGoogleHours(oh, cacheKey);
    hoursCache[cacheKey] = result;
    renderHoursBadge(result);

    console.log('[Hours] ✓', p.name, result.isOpen ? 'Açık' : 'Kapalı');

  } catch(e) {
    console.warn('[Hours] Edge Function hatası:', e);
    badge.style.display = 'none';
  }
}"""

if old1 in html:
    html = html.replace(old1, new1)
    patches.append("✓ Patch 1: fetchFromGoogle → Edge Function proxy")
else:
    patches.append("✗ Patch 1 BULUNAMADI")

# ══════════════════════════════════════════════════════════════════════════════
# Kaydet
# ══════════════════════════════════════════════════════════════════════════════
if html != original:
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n{'='*58}")
    print("CrewGuide patch24 — Edge Function proxy")
    print('='*58)
    for p in patches:
        print(f"  {p}")
    print(f"""
── Sonraki adımlar ──────────────────────────────────────
  1. Supabase Dashboard → Edge Functions → Deploy
     (places-hours/index.ts dosyasını yapıştır)

  2. Edge Function'a secret ekle:
     Dashboard → Edge Functions → places-hours → Secrets
     GOOGLE_PLACES_KEY = AIza...senin_key...

  3. python deploy.py "patch24: edge function proxy"
{'='*58}
""")
else:
    print("\n⚠️  Değişiklik yapılmadı.")
    for p in patches:
        print(f"  {p}")
