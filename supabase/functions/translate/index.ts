// Supabase Edge Function: translate v3
// Sadece giriş yapmış kullanıcılar çağırabilir (Anthropic kredisi korunur).
import { CORS, json, getCaller } from "../_shared/auth.ts";

const ANTHROPIC_API_KEY = Deno.env.get("ANTHROPIC_API_KEY") ?? "";
const MAX_CHARS = 2000;

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });

  try {
    const caller = await getCaller(req);
    if (!caller.user && !caller.isService) return json({ error: "Giriş gerekli" }, 401);

    const { text, targetLang } = await req.json().catch(() => ({}));
    if (!text || !targetLang) return json({ error: "text and targetLang required" }, 400);
    if (String(text).length > MAX_CHARS) return json({ error: "Metin çok uzun" }, 413);
    if (!ANTHROPIC_API_KEY) return json({ error: "ANTHROPIC_API_KEY yok" }, 500);

    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 500,
        messages: [{
          role: "user",
          content: `Translate this text to ${String(targetLang).slice(0, 30)}. Return ONLY the translation, no explanations:\n\n${text}`,
        }],
      }),
    });

    const data = await res.json();
    if (!res.ok) return json({ error: data?.error?.message || "Çeviri hatası" }, 502);
    const translation = data.content?.[0]?.text?.trim();
    return json({ translation });
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
});
