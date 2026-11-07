// Supabase Edge Function: send-push v20
// - { test: true }: giriş yapmış kullanıcının KENDİ cihazına deneme bildirimi; cihaz bazında sonuç döner.
// - Yer bildirimi (placeId): veritabanı tetikleyicisi yer yayına girince çağırır; her yer için EN FAZLA BİR KEZ
//   gider (places.push_sent_at atomik işaretlenir). Onay bekleyen veya gizli yerler için bildirim gönderilmez.
// - placeId olmadan serbest duyuru: sadece admin / şehir elçisi / sunucu (service key).
// - Bildirim metni her abonenin kendi dilinde (push_subscriptions.lang).
import { CORS, getCaller, getKeys } from "../_shared/auth.ts";

const VAPID_PUBLIC_KEY = Deno.env.get("VAPID_PUBLIC_KEY") ?? "";
const VAPID_PRIVATE_KEY = Deno.env.get("VAPID_PRIVATE_KEY") ?? "";
const VAPID_EMAIL = Deno.env.get("VAPID_EMAIL") ?? "";
// VAPID "sub" alanı mailto: veya https: ile başlamalı (Apple bunu zorunlu tutar, yoksa 403 BadJwtToken)
const VAPID_SUB = /^(mailto:|https:)/i.test(VAPID_EMAIL) ? VAPID_EMAIL : `mailto:${VAPID_EMAIL || "admin@crewguide.fyi"}`;

const TEST_MESSAGES: Record<string, string> = {
  tr: "Bildirimler çalışıyor ✓",
  en: "Notifications are working ✓",
  de: "Benachrichtigungen funktionieren ✓",
  fr: "Les notifications fonctionnent ✓",
  es: "Las notificaciones funcionan ✓",
  ar: "الإشعارات تعمل ✓",
  ja: "通知は正常に動作しています ✓",
  ko: "알림이 작동합니다 ✓",
  zh: "通知功能正常 ✓",
};

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
    const { url: SUPABASE_URL, serviceKey: SUPABASE_SERVICE_KEY } = getKeys();
    const body = await req.json().catch(() => ({}));
    const subHeaders = { "apikey": SUPABASE_SERVICE_KEY, "Authorization": `Bearer ${SUPABASE_SERVICE_KEY}` };

    // Deneme bildirimi: sadece isteyen kullanıcının kendi aboneliğine
    if (body.test === true) {
      if (!caller.user) return reply({ ok: false, error: "Giriş gerekli" }, 401);
      const r = await fetch(
        `${SUPABASE_URL}/rest/v1/push_subscriptions?user_id=eq.${caller.user.id}&select=endpoint,p256dh,auth,lang,city`,
        { headers: subHeaders });
      const mine = await r.json().catch(() => []);
      if (!Array.isArray(mine) || !mine.length) return reply({ ok: false, error: "no subscription" }, 404);
      const vapidKey = await importVapidKey();
      const results = [];
      for (const s of mine) {
        const out = await pushOne(s, {
          title: "✈️ CrewGuide",
          body: TEST_MESSAGES[(s.lang || "tr").toLowerCase()] || TEST_MESSAGES.en,
          icon: "/icons/icon-192.png",
          tag: "crewguide-test",
          data: { url: "/" },
        }, vapidKey, SUPABASE_URL, subHeaders);
        results.push({ host: hostOf(s.endpoint), city: s.city, ...out });
      }
      console.log("[send-push] test:", JSON.stringify(results));
      return reply({ ok: results.some(x => x.ok), results });
    }

    let city = "";
    let placeName = "";
    const placeId = String(body.placeId ?? body.record?.id ?? "").slice(0, 200);

    if (placeId) {
      // Yer bildirimi: herkes tetikleyebilir ama her yer için EN FAZLA BİR KEZ gider.
      // Yer yayında değilse ya da daha önce bildirildiyse hiçbir şey olmaz (atomik işaretleme).
      const pr = await fetch(
        `${SUPABASE_URL}/rest/v1/places?id=eq.${encodeURIComponent(placeId)}&push_sent_at=is.null&status=eq.approved&or=(is_hidden.is.null,is_hidden.eq.false)&select=name,city`,
        {
          method: "PATCH",
          headers: {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": `Bearer ${SUPABASE_SERVICE_KEY}`,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
          },
          body: JSON.stringify({ push_sent_at: new Date().toISOString() }),
        }
      );
      const rows = await pr.json().catch(() => []);
      const row = Array.isArray(rows) ? rows[0] : null;
      if (!pr.ok) {
        console.error("[send-push] place update failed:", pr.status, JSON.stringify(rows).slice(0, 200));
        return reply({ ok: false, error: "place check failed" }, 500);
      }
      if (!row) return reply({ ok: true, sent: 0, msg: "already sent or not published" });
      city = row.city || "";
      placeName = row.name || "";
    } else {
      // Yer kimliği olmayan serbest duyuru: sadece admin / şehir elçisi / sunucu
      if (!caller.isTrusted) return reply({ ok: false, error: "Yetkisiz" }, 403);
      city = String(body.city ?? "").slice(0, 100);
      placeName = String(body.name ?? "").slice(0, 120);
    }
    if (!city) return reply({ ok: false, error: "city gerekli" }, 400);

    console.log("[send-push] city:", city, "place:", placeName, "by:", caller.role);

    // Şehir eşleşmesi büyük/küçük harf duyarsız (ör. "istanbul" / "Istanbul")
    const cityQ = encodeURIComponent('"' + city.replace(/["\\]/g, "") + '"');
    const subUrl = (cols: string) =>
      `${SUPABASE_URL}/rest/v1/push_subscriptions?or=(city.eq.${cityQ},city.ilike.${cityQ})&select=${cols}`;
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
      const out = await pushOne(s, {
        title: "✈️ CrewGuide",
        body: messageFor(s.lang, city, placeName || "📍"),
        icon: "/icons/icon-192.png",
        tag: "new-place-" + (placeId || city),
        data: { url: "/", placeId, city },
      }, vapidKey, SUPABASE_URL, subHeaders);
      if (out.ok) sent++;
    }

    console.log("[send-push] sent:", sent, "/", subs.length);
    return reply({ ok: true, sent, total: subs.length });

  } catch (e) {
    console.error("[send-push] fatal:", String(e));
    return reply({ ok: false, error: String(e) }, 500);
  }
});

function hostOf(endpoint: string): string {
  try { return new URL(endpoint).host; } catch { return "?"; }
}

// Tek bir cihaza gönder. Süresi dolmuş aboneliği (404/410) siler.
async function pushOne(
  s: { endpoint?: string; p256dh?: string; auth?: string },
  notification: Record<string, unknown>,
  vapidKey: CryptoKey,
  supabaseUrl: string,
  subHeaders: Record<string, string>,
): Promise<{ ok: boolean; status: number; error?: string }> {
  if (!s.endpoint || !s.p256dh || !s.auth) return { ok: false, status: 0, error: "incomplete subscription" };
  try {
    const encrypted = await encryptPayload(JSON.stringify(notification), s.p256dh, s.auth);
    const jwt = await makeVapidJwt(s.endpoint, vapidKey);
    const pushRes = await fetch(s.endpoint, {
      method: "POST",
      headers: {
        "Authorization": `vapid t=${jwt}, k=${VAPID_PUBLIC_KEY}`,
        "Content-Type": "application/octet-stream",
        "Content-Encoding": "aes128gcm",
        "TTL": "86400",
        "Urgency": "normal",
      },
      body: encrypted,
    });
    if (pushRes.ok) return { ok: true, status: pushRes.status };
    const text = (await pushRes.text().catch(() => "")).slice(0, 200);
    console.error("[send-push] error:", hostOf(s.endpoint), pushRes.status, text);
    if (pushRes.status === 404 || pushRes.status === 410) {
      await fetch(`${supabaseUrl}/rest/v1/push_subscriptions?endpoint=eq.${encodeURIComponent(s.endpoint)}`,
        { method: "DELETE", headers: subHeaders }).catch(() => {});
    }
    return { ok: false, status: pushRes.status, error: text };
  } catch (e) {
    console.error("[send-push] exception:", hostOf(s.endpoint), String(e));
    return { ok: false, status: 0, error: String(e).slice(0, 200) };
  }
}

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
  const p = b64url(JSON.stringify({ aud: audience, exp, sub: VAPID_SUB }));
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