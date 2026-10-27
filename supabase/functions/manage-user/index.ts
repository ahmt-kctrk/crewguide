// Supabase Edge Function: manage-user v2
// SUPABASE_SECRET_KEYS kullanıyor (yeni format)

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: CORS_HEADERS });
  }

  try {
    const { action, targetUserId } = await req.json();

    if (!action || !targetUserId) {
      return json({ error: "action ve targetUserId gerekli" }, 400);
    }

    const authHeader = req.headers.get("Authorization") || "";
    const userToken = authHeader.replace("Bearer ", "");

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;

    // Secret keys — yeni format (JSON dict)
    const secretKeysRaw = Deno.env.get("SUPABASE_SECRET_KEYS");
    const anonKeysRaw   = Deno.env.get("SUPABASE_PUBLISHABLE_KEYS");

    let serviceRoleKey = "";
    let anonKey = "";

    if (secretKeysRaw) {
      try {
        const parsed = JSON.parse(secretKeysRaw);
        // İlk değeri al
        serviceRoleKey = Object.values(parsed)[0] as string;
      } catch {
        serviceRoleKey = secretKeysRaw;
      }
    }

    // Fallback: deprecated key
    if (!serviceRoleKey) {
      serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
    }

    if (anonKeysRaw) {
      try {
        const parsed = JSON.parse(anonKeysRaw);
        anonKey = Object.values(parsed)[0] as string;
      } catch {
        anonKey = anonKeysRaw;
      }
    }

    if (!anonKey) {
      anonKey = Deno.env.get("SUPABASE_ANON_KEY") || "";
    }

    if (!serviceRoleKey) {
      return json({ error: "Service role key bulunamadı" }, 500);
    }

    // İsteği yapanı doğrula
    const anonClient = createClient(supabaseUrl, anonKey, {
      global: { headers: { Authorization: authHeader } }
    });

    const { data: { user }, error: userError } = await anonClient.auth.getUser(userToken);
    if (userError || !user) {
      return json({ error: "Yetkisiz" }, 401);
    }

    // Admin client
    const adminClient = createClient(supabaseUrl, serviceRoleKey);

    // Caller'ın rolünü kontrol et
    const { data: callerProfile } = await adminClient
      .from("profiles")
      .select("role")
      .eq("id", user.id)
      .single();

    const isAdmin = callerProfile?.role === "admin";
    const isSelf  = user.id === targetUserId;

    // ── DEVRE DIŞI ─────────────────────────────────────────────────────────
    if (action === "disable") {
      if (!isSelf) return json({ error: "Sadece kendi hesabını devre dışı bırakabilirsin" }, 403);

      await adminClient.from("profiles")
        .update({ is_disabled: true, disabled_at: new Date().toISOString() })
        .eq("id", targetUserId);

      await adminClient.auth.admin.updateUserById(targetUserId, {
        ban_duration: "876600h"
      });

      return json({ success: true, action: "disabled" });
    }

    // ── SİL ────────────────────────────────────────────────────────────────
    if (action === "delete") {
      if (!isAdmin) return json({ error: "Sadece adminler kullanıcı silebilir" }, 403);
      if (isSelf)   return json({ error: "Kendi hesabını silemezsin" }, 400);

      await adminClient.from("profiles").delete().eq("id", targetUserId);
      await adminClient.from("invite_codes").delete().eq("created_by", targetUserId);
      await adminClient.from("places").update({ is_hidden: true }).eq("user_id", targetUserId);

      const { error: deleteError } = await adminClient.auth.admin.deleteUser(targetUserId);
      if (deleteError) return json({ error: "Auth silme hatası: " + deleteError.message }, 500);

      return json({ success: true, action: "deleted" });
    }

    // ── AKTİF ET ───────────────────────────────────────────────────────────
    if (action === "enable") {
      if (!isAdmin) return json({ error: "Sadece adminler hesap aktif edebilir" }, 403);

      await adminClient.from("profiles")
        .update({ is_disabled: false, disabled_at: null })
        .eq("id", targetUserId);

      await adminClient.auth.admin.updateUserById(targetUserId, { ban_duration: "none" });

      return json({ success: true, action: "enabled" });
    }

    return json({ error: "Geçersiz action" }, 400);

  } catch (e) {
    return json({ error: e.message }, 500);
  }
});

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
}