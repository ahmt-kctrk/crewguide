const ANTHROPIC_API_KEY = Deno.env.get("ANTHROPIC_API_KEY")!;

Deno.serve(async (req: Request) => {
  // CORS
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
      }
    });
  }

  try {
    const { text, targetLang } = await req.json();
    if (!text || !targetLang) {
      return Response.json({ error: "text and targetLang required" }, { status: 400 });
    }

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
          content: `Translate this text to ${targetLang}. Return ONLY the translation, no explanations:\n\n${text}`
        }]
      })
    });

    const data = await res.json();
    const translation = data.content?.[0]?.text?.trim();

    return new Response(
      JSON.stringify({ translation }),
      { headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } }
    );
  } catch (e) {
    return Response.json({ error: String(e) }, { status: 500 });
  }
});