// Ortak yardımcılar: CORS, anahtarlar, isteği yapan kullanıcıyı ve rolünü doğrulama.
// Tüm fonksiyonlar buradan import eder; deploy sırasında otomatik paketlenir.
import { createClient, SupabaseClient, User } from "https://esm.sh/@supabase/supabase-js@2";

export const ADMIN_EMAIL = "ahmtkctrk@gmail.com";

export const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

export function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

// Yeni (JSON sözlük) ve eski anahtar formatlarını destekle
function firstKey(raw: string | undefined): string {
  if (!raw) return "";
  try { return Object.values(JSON.parse(raw))[0] as string; } catch { return raw; }
}

export function getKeys() {
  const url = Deno.env.get("SUPABASE_URL") ?? "";
  const serviceKey = firstKey(Deno.env.get("SUPABASE_SECRET_KEYS")) || Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  const anonKey = firstKey(Deno.env.get("SUPABASE_PUBLISHABLE_KEYS")) || Deno.env.get("SUPABASE_ANON_KEY") || "";
  return { url, serviceKey, anonKey };
}

export function adminClient(): SupabaseClient {
  const { url, serviceKey } = getKeys();
  return createClient(url, serviceKey, { auth: { persistSession: false } });
}

export type Caller = {
  user: User | null;        // giriş yapmış kullanıcı (yoksa null)
  role: string;             // 'admin' | 'ambassador' | 'user' | 'anon' | 'service'
  isAdmin: boolean;
  isTrusted: boolean;       // admin veya şehir elçisi
  isService: boolean;       // service-role anahtarıyla gelen sunucu çağrısı (ör. DB webhook)
};

function bearer(req: Request): string {
  return (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "").trim();
}

// JWT içindeki "role" alanını oku (imzayı burada doğrulamıyoruz; service rolü ayrıca anahtar eşleşmesiyle kontrol ediliyor)
function jwtRole(token: string): string {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return payload.role || "";
  } catch { return ""; }
}

export async function getCaller(req: Request): Promise<Caller> {
  const token = bearer(req);
  const { url, anonKey, serviceKey } = getKeys();
  const none: Caller = { user: null, role: "anon", isAdmin: false, isTrusted: false, isService: false };
  if (!token) return none;

  // Sunucu çağrısı: service anahtarının kendisi
  const legacyService = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if ((serviceKey && token === serviceKey) || (legacyService && token === legacyService)) {
    return { user: null, role: "service", isAdmin: true, isTrusted: true, isService: true };
  }
  // Herkese açık anon anahtar → kullanıcı yok
  if (jwtRole(token) === "anon" || token === anonKey) return none;

  // Kullanıcı token'ı → Supabase Auth ile doğrula
  const client = createClient(url, anonKey, { auth: { persistSession: false } });
  const { data, error } = await client.auth.getUser(token);
  if (error || !data?.user) return none;
  const user = data.user;

  const { data: prof } = await adminClient().from("profiles").select("role, is_disabled").eq("id", user.id).maybeSingle();
  if (prof?.is_disabled) return none;
  const isAdmin = user.email === ADMIN_EMAIL || prof?.role === "admin";
  const role = isAdmin ? "admin" : (prof?.role || "user");
  return { user, role, isAdmin, isTrusted: isAdmin || role === "ambassador", isService: false };
}
