// Supabase Edge Function: send-push v18
// - Sadece admin / şehir elçisi / sunucu (service key) çağırabilir → bildirim spam'i engellenir.
// - Onay bekleyen veya gizli yerler için bildirim gönderilmez.
// - Bildirim metni her abonenin kendi dilinde (push_subscriptions.lang).
import { CORS, getCaller, getKeys } from "../_shared/auth.ts";

const VAPID_PUBLIC_KEY = Deno.env.get("VAPID_PUBLIC_KEY") ?? "";
const VAPID_PRIVATE_KEY = Deno.env.get("VAPID_PRIVATE_KEY") ?? "";
const VAPID_EMAIL = Deno.env.get("VAPID_EMAIL") ?? "";

// {city} / {place} yer tutucuları
const MESSAGES: Record<string, string> = {
  tr: "{city} için yeni yer: {place}",
  en: "New place in {city}: {place}",
  de: "Neuer Ort in {city}: {place}",
  fr: "Nouveau lieu à {city} : {place}",
  es: "Nuevo lugar en {city}: {place}",
  ar: "مكان جديد في {city}: {place}",
  ja: "{city}に新しいスポット：{place}",
  ko: "{city}에 새 장소: {place}",
  zh: "{city}新地点：{place}",
};

function messageFor(lang: string | null | undefined, city: string, place: string) {
  const tpl = MESSAGES[(lang || "tr").toLowerCase()] || MESSAGES.en;
  return tpl.replace("{city}", city).replace("{place}", place);
}

function reply(data: unknown, status = 200) {
  return Response.json(data, { status, headers: CORS });
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS });
  }

  try {
    const caller = await getCaller(req);
    if (!caller.isTrusted) {
      return reply({ ok: false, error: "Yetkisiz" }, 403);
    }

    const { url: SUPABASE_URL, serviceKey: SUPABASE_SERVICE_KEY } = getKeys();
    const body = await req.json().catch(() => ({}));
    let city = "";
    let placeName = "";
    let placeId = "";

    if (body.type === "INSERT" && body.record) {
      // DB webhook: sadece yayında olan yerler için bildir
      if (body.record.is_hidden || body.record.status === "pending") {
        return reply({ ok: true, sent: 0, msg: "not published" });
      }
      city = body.record.city ?? "";
      placeName = body.record.name ?? "";
      placeId = body.record.id ?? "";
    } else if (body.city) {
      city = String(body.city).slice(0, 100);
      placeName = String(body.name ?? "").slice(0, 120);
      placeId = String(body.placeId ?? "");
    }
    if (!city) return reply({ ok: false, error: "city gerekli" }, 400);

    // Yer kimliği verildiyse gerçekten yayında olduğunu doğrula
    if (placeId) {
      const pr = await fetch(
        `${SUPABASE_URL}/rest/v1/places?id=eq.${encodeURIComponent(placeId)}&select=name,city,is_hidden`,
        { headers: { "apikey": SUPABASE_SERVICE_KEY, "Authorization": `Bearer ${SUPABASE_SERVICE_KEY}` } }
      );
      const rows = await pr.json().catch(() => []);
      const row = Array.isArray(rows) ? rows[0] : null;
      if (row?.is_hidden) return reply({ ok: true, sent: 0, msg: "not published" });
      if (row) { city = row.city || city; placeName = row.name || placeName; }
    }

    console.log("[send-push] city:", city, "place:", placeName, "by:", caller.role);

    const subUrl = (cols: string) =>
      `${SUPABASE_URL}/rest/v1/push_subscriptions?city=eq.${encodeURIComponent(city)}&select=${cols}`;
    const subHeaders = { "apikey": SUPABASE_SERVICE_KEY, "Authorization": `Bearer ${SUPABASE_SERVICE_KEY}` };
    let res = await fetch(subUrl("endpoint,p256dh,auth,lang"), { headers: subHeaders });
    if (!res.ok) res = await fetch(subUrl("endpoint,p256dh,auth"), { headers: subHeaders }); // lang kolonu yoksa
    const subs = await res.json();
    console.log("[send-push] subs:", Array.isArray(subs) ? subs.length : 0);

    if (!Array.isArray(subs) || subs.length === 0) {
      return reply({ ok: true, sent: 0, msg: "no subscribers" });
    }

    const vapidKey = await importVapidKey();

    let sent = 0;
    for (const s of subs) {
      if (!s.endpoint) continue;
      try {
        const notification = JSON.stringify({
          title: "✈️ CrewGuide",
          body: messageFor(s.lang, city, placeName || "📍"),
          icon: "/icons/icon-192.png",
          tag: "new-place-" + (placeId || city),
          data: { url: "/", placeId, city },
        });
        const encrypted = await encryptPayload(notification, s.p256dh, s.auth);
        const jwt = await makeVapidJwt(s.endpoint, vapidKey);
        const pushRes = await fetch(s.endpoint, {
          method: "POST",
          headers: {
            "Authorization": `vapid t=${jwt}, k=${VAPID_PUBLIC_KEY}`,
            "Content-Type": "application/octet-stream",
            "Content-Encoding": "aes128gcm",
            "TTL": "86400",
          },
          body: encrypted,
        });
        console.log("[send-push] status:", pushRes.status);
        if (pushRes.ok || pushRes.status === 201) sent++;
        else {
          console.error("[send-push] error:", await pushRes.text());
          // Süresi dolmuş abonelikleri temizle
          if (pushRes.status === 404 || pushRes.status === 410) {
            await fetch(`${SUPABASE_URL}/rest/v1/push_subscriptions?endpoint=eq.${encodeURIComponent(s.endpoint)}`,
              { method: "DELETE", headers: subHeaders }).catch(() => {});
          }
        }
      } catch (e) {
        console.error("[send-push] exception:", String(e));
      }
    }

    console.log("[send-push] sent:", sent, "/", subs.length);
    return reply({ ok: true, sent, total: subs.length });

  } catch (e) {
    console.error("[send-push] fatal:", String(e));
    return reply({ ok: false, error: String(e) }, 500);
  }
});

async function importVapidKey(): Promise<CryptoKey> {
  const rawPrivate = fromB64url(VAPID_PRIVATE_KEY);
  const rawPublic = fromB64url(VAPID_PUBLIC_KEY);
  const jwk = {
    kty: "EC", crv: "P-256",
    d: toB64url(rawPrivate),
    x: toB64url(rawPublic.slice(1, 33)),
    y: toB64url(rawPublic.slice(33, 65)),
  };
  return crypto.subtle.importKey("jwk", jwk, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
}

async function makeVapidJwt(endpoint: string, key: CryptoKey): Promise<string> {
  const url = new URL(endpoint);
  const audience = `${url.protocol}//${url.host}`;
  const exp = Math.floor(Date.now() / 1000) + 43200;
  const h = b64url(JSON.stringify({ typ: "JWT", alg: "ES256" }));
  const p = b64url(JSON.stringify({ aud: audience, exp, sub: VAPID_EMAIL }));
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, enc(`${h}.${p}`));
  return `${h}.${p}.${toB64url(new Uint8Array(sig))}`;
}

async function encryptPayload(payload: string, p256dhB64: string, authB64: string): Promise<Uint8Array> {
  const receiverPublic = fromB64url(p256dhB64);
  const authSecret = fromB64url(authB64);
  const salt = crypto.getRandomValues(new Uint8Array(16));

  const ephemeral = await crypto.subtle.generateKey({ name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]);
  const ephemeralPublicRaw = new Uint8Array(await crypto.subtle.exportKey("raw", ephemeral.publicKey));

  const receiverKey = await crypto.subtle.importKey("raw", receiverPublic, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const sharedBits = new Uint8Array(await crypto.subtle.deriveBits({ name: "ECDH", public: receiverKey }, ephemeral.privateKey, 256));

  const prk = await hkdf(authSecret, sharedBits, concat(enc("WebPush: info\x00"), receiverPublic, ephemeralPublicRaw), 32);
  const cek = await hkdf(salt, prk, concat(enc("Content-Encoding: aes128gcm\x00"), new Uint8Array([1])), 16);
  const nonce = await hkdf(salt, prk, concat(enc("Content-Encoding: nonce\x00"), new Uint8Array([1])), 12);

  const aesKey = await crypto.subtle.importKey("raw", cek, "AES-GCM", false, ["encrypt"]);
  const payloadBytes = concat(enc(payload), new Uint8Array([2]));
  const ciphertext = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, aesKey, payloadBytes));

  const rs = new Uint8Array(4);
  new DataView(rs.buffer).setUint32(0, 4096, false);
  return concat(salt, rs, new Uint8Array([ephemeralPublicRaw.length]), ephemeralPublicRaw, ciphertext);
}

async function hkdf(salt: Uint8Array, ikm: Uint8Array, info: Uint8Array, len: number): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "HKDF", hash: "SHA-256", salt, info }, key, len * 8);
  return new Uint8Array(bits);
}

function b64url(str: string): string {
  return btoa(unescape(encodeURIComponent(str))).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

function toB64url(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

function fromB64url(str: string): Uint8Array {
  const b64 = str.replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(b64 + "==".slice(0, (4 - b64.length % 4) % 4)), c => c.charCodeAt(0));
}

function enc(str: string): Uint8Array {
  return new TextEncoder().encode(str);
}

function concat(...arrays: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(arrays.reduce((s, a) => s + a.length, 0));
  let i = 0;
  for (const a of arrays) { out.set(a, i); i += a.length; }
  return out;
}