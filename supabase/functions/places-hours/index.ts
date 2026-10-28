// Supabase Edge Function: places-hours v6
// Sadece giriş yapmış kullanıcılar çağırabilir (Google Places kredisi korunur).
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { CORS, getCaller } from "../_shared/auth.ts";

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  const caller = await getCaller(req);
  if (!caller.user && !caller.isService) return json({ error: "Giriş gerekli" }, 401);

  let name = '', addr = '', placeId = null;
  try {
    const bodyText = await req.text();
    if (bodyText) { const p = JSON.parse(bodyText); name=String(p.name||'').slice(0,200); addr=String(p.addr||'').slice(0,300); placeId=p.placeId||null; }
    if (placeId && !/^[A-Za-z0-9_-]{10,300}$/.test(String(placeId))) placeId = null;
    if (!placeId && !name) return json({ error: "name gerekli" }, 400);
  } catch(e) { return json({ error: "Body parse: " + (e as Error).message }, 400); }

  const KEY = Deno.env.get("GOOGLE_PLACES_KEY");
  if (!KEY) return json({ error: "GOOGLE_PLACES_KEY yok" }, 500);

  try {
    let googlePlaceId = placeId;

    if (!googlePlaceId) {
      const textQuery = `${name} ${addr}`.trim();
      const sr = await fetch("https://places.googleapis.com/v1/places:searchText", {
        method: "POST",
        headers: { "Content-Type":"application/json", "X-Goog-Api-Key":KEY, "X-Goog-FieldMask":"places.id" },
        body: JSON.stringify({ textQuery, maxResultCount: 1 }),
      });
      const sd = await sr.json();
      console.log("Search:", JSON.stringify(sd).slice(0,200));
      // Google hatası (geçersiz anahtar, API kapalı, kota) "bulunamadı" gibi görünmesin
      if (!sr.ok || sd.error) {
        console.error("Google search error:", sr.status, JSON.stringify(sd.error || sd).slice(0, 300));
        return json({ error: "Google: " + (sd.error?.message || sr.status), google_status: sd.error?.status || sr.status }, 502);
      }
      if (!sd.places?.[0]?.id) return json({ found: false });
      googlePlaceId = sd.places[0].id;
    }

    // Place Details — tüm alanları iste, sonra filtrele
    const dr = await fetch(`https://places.googleapis.com/v1/places/${googlePlaceId}`, {
      headers: {
        "X-Goog-Api-Key": KEY,
        "X-Goog-FieldMask": "id,displayName,regularOpeningHours",
      },
    });

    const drText = await dr.text();
    console.log("Detail raw:", drText.slice(0, 500));

    let dd: any = {};
    try { dd = JSON.parse(drText); } catch(e) { return json({ error: "Detail parse: " + (e as Error).message + " raw: " + drText.slice(0,100) }, 500); }

    if (!dr.ok || dd.error) {
      console.error("Google detail error:", dr.status, JSON.stringify(dd.error || dd).slice(0, 300));
      return json({ error: "Google: " + (dd.error?.message || dr.status), google_status: dd.error?.status || dr.status }, 502);
    }

    const oh = dd.regularOpeningHours;
    if (!oh) return json({ found: true, google_place_id: googlePlaceId, opening_hours: null });

    return json({
      found: true,
      google_place_id: googlePlaceId,
      opening_hours: {
        open_now: oh.openNow ?? false,
        periods: (oh.periods || []).map((p: any) => ({
          open: { day: p.open?.day??0, time: p.open?.hour!==undefined ? String(p.open.hour).padStart(2,'0')+String(p.open.minute??0).padStart(2,'0') : '0000' },
          close: p.close ? { day: p.close.day??0, time: String(p.close.hour).padStart(2,'0')+String(p.close.minute??0).padStart(2,'0') } : null
        })),
        weekday_text: oh.weekdayDescriptions || [],
      }
    });

  } catch(e) {
    console.error("Error:", (e as Error).message);
    return json({ error: (e as Error).message }, 500);
  }
});

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { ...CORS, "Content-Type": "application/json" } });
}