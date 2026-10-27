// Supabase Edge Function: places-hours v5
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  let name = '', addr = '', placeId = null;
  try {
    const bodyText = await req.text();
    if (bodyText) { const p = JSON.parse(bodyText); name=p.name||''; addr=p.addr||''; placeId=p.placeId||null; }
  } catch(e) { return json({ error: "Body parse: " + e.message }, 400); }

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
    try { dd = JSON.parse(drText); } catch(e) { return json({ error: "Detail parse: " + e.message + " raw: " + drText.slice(0,100) }, 500); }

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
    console.error("Error:", e.message);
    return json({ error: e.message }, 500);
  }
});

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { ...CORS, "Content-Type": "application/json" } });
}