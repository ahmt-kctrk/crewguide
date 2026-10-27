const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const VAPID_PUBLIC_KEY = Deno.env.get("VAPID_PUBLIC_KEY") ?? "";
const VAPID_PRIVATE_KEY = Deno.env.get("VAPID_PRIVATE_KEY") ?? "";
const VAPID_EMAIL = Deno.env.get("VAPID_EMAIL") ?? "";

// ── CORS headers — tüm response'lara eklenir ─────────────────────────────────
const CORS = {
  "Access-Control-Allow-Origin":  "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req: Request) => {
  // Preflight — browser her POST öncesi bunu gönderir
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS });
  }

  try {
    const body = await req.json().catch(() => ({}));
    let city = "";
    let placeName = "Yeni yer";

    if (body.type === "INSERT" && body.record) {
      city = body.record.city ?? "";
      placeName = body.record.name ?? "Yeni yer";
    } else if (body.city) {
      city = body.city;
      placeName = body.name ?? "Yeni yer";
    }

    console.log("[send-push] city:", city, "place:", placeName);

    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/push_subscriptions?city=eq.${encodeURIComponent(city)}&select=endpoint,p256dh,auth`,
      { headers: { "apikey": SUPABASE_SERVICE_KEY, "Authorization": `Bearer ${SUPABASE_SERVICE_KEY}` } }
    );
    const subs = await res.json();
    console.log("[send-push] subs:", Array.isArray(subs) ? subs.length : 0);

    if (!Array.isArray(subs) || subs.length === 0) {
      return Response.json({ ok: true, sent: 0, msg: "no subscribers" }, { headers: CORS });
    }

    const vapidKey = await importVapidKey();
    const notification = JSON.stringify({
      title: "✈️ CrewGuide",
      body: `${city} için yeni yer: ${placeName}`,
      icon: "/icons/icon-192.png",
      tag: "new-place",
      data: { url: "/" }
    });

    let sent = 0;
    for (const s of subs) {
      if (!s.endpoint) continue;
      try {
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
        else console.error("[send-push] error:", await pushRes.text());
      } catch (e) {
        console.error("[send-push] exception:", String(e));
      }
    }

    console.log("[send-push] sent:", sent, "/", subs.length);
    return Response.json({ ok: true, sent, total: subs.length }, { headers: CORS });

  } catch (e) {
    console.error("[send-push] fatal:", String(e));
    return Response.json({ ok: false, error: String(e) }, { status: 500, headers: CORS });
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