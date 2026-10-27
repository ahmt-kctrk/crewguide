// Supabase Edge Function: manage-user v3
// action:
//   disable      → kullanıcı kendi hesabını devre dışı bırakır
//   delete_self  → kullanıcı kendi hesabını KALICI siler (App Store / KVKK gereği)
//   delete       → admin başka bir kullanıcıyı siler
//   enable       → admin devre dışı hesabı açar
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { CORS, json, getCaller, adminClient } from "../_shared/auth.ts";

const DELETED_NAME = "Silinmiş kullanıcı";

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  try {
    const { action, targetUserId } = await req.json().catch(() => ({}));
    if (!action) return json({ error: "action gerekli" }, 400);

    const caller = await getCaller(req);
    if (!caller.user) return json({ error: "Yetkisiz" }, 401);

    const db = adminClient();
    const target = action === "delete_self" ? caller.user.id : targetUserId;
    if (!target) return json({ error: "targetUserId gerekli" }, 400);
    const isSelf = caller.user.id === target;

    // ── DEVRE DIŞI ─────────────────────────────────────────────────────────
    if (action === "disable") {
      if (!isSelf) return json({ error: "Sadece kendi hesabını devre dışı bırakabilirsin" }, 403);
      await db.from("profiles").update({ is_disabled: true, disabled_at: new Date().toISOString() }).eq("id", target);
      await db.auth.admin.updateUserById(target, { ban_duration: "876600h" });
      return json({ success: true, action: "disabled" });
    }

    // ── KENDİ HESABINI SİL ────────────────────────────────────────────────
    if (action === "delete_self") {
      if (caller.isAdmin) return json({ error: "Admin hesabı buradan silinemez" }, 400);
      const report = await wipeUserData(db, target, "anonymize");
      const { error } = await db.auth.admin.deleteUser(target);
      if (error) return json({ error: "Auth silme hatası: " + error.message, report }, 500);
      return json({ success: true, action: "deleted_self", report });
    }

    // ── ADMIN: SİL ─────────────────────────────────────────────────────────
    if (action === "delete") {
      if (!caller.isAdmin) return json({ error: "Sadece adminler kullanıcı silebilir" }, 403);
      if (isSelf) return json({ error: "Kendi hesabını silemezsin" }, 400);
      const report = await wipeUserData(db, target, "hide");
      const { error } = await db.auth.admin.deleteUser(target);
      if (error) return json({ error: "Auth silme hatası: " + error.message, report }, 500);
      return json({ success: true, action: "deleted", report });
    }

    // ── ADMIN: AKTİF ET ────────────────────────────────────────────────────
    if (action === "enable") {
      if (!caller.isAdmin) return json({ error: "Sadece adminler hesap aktif edebilir" }, 403);
      await db.from("profiles").update({ is_disabled: false, disabled_at: null }).eq("id", target);
      await db.auth.admin.updateUserById(target, { ban_duration: "none" });
      return json({ success: true, action: "enabled" });
    }

    return json({ error: "Geçersiz action" }, 400);
  } catch (e) {
    return json({ error: (e as Error).message }, 500);
  }
});

// Kullanıcının kişisel verilerini temizle.
//  placesMode "anonymize": eklediği yerler yayında kalır ama kullanıcıyla bağı koparılır (kendi silme)
//  placesMode "hide":      eklediği yerler gizlenir (admin silme — eski davranış)
// Her adım ayrı; bir tablo/kolon yoksa diğerleri yine çalışır.
async function wipeUserData(db: ReturnType<typeof adminClient>, uid: string, placesMode: "anonymize" | "hide") {
  const report: Record<string, string> = {};
  const step = async (name: string, fn: () => PromiseLike<{ error: unknown }>) => {
    try {
      const { error } = await fn();
      report[name] = error ? "hata: " + ((error as { message?: string }).message || String(error)) : "ok";
    } catch (e) { report[name] = "hata: " + String(e); }
  };

  await step("favorites", () => db.from("favorites").delete().eq("user_id", uid));
  await step("push_subscriptions", () => db.from("push_subscriptions").delete().eq("user_id", uid));
  await step("invite_codes", () => db.from("invite_codes").delete().eq("created_by", uid));

  // Yorumlar: içerik kalır, isim ve kullanıcı bağı silinir
  await step("comments", () => db.from("comments").update({ user_id: null, username: DELETED_NAME }).eq("user_id", uid));
  if (report.comments !== "ok") await step("comments_delete", () => db.from("comments").delete().eq("user_id", uid));

  // Puanlar: ortalama bozulmasın diye anonimleştir, olmazsa sil
  await step("ratings", () => db.from("ratings").update({ user_id: null }).eq("user_id", uid));
  if (report.ratings !== "ok") await step("ratings_delete", () => db.from("ratings").delete().eq("user_id", uid));

  if (placesMode === "anonymize") {
    await step("places", () => db.from("places").update({ user_id: null }).eq("user_id", uid));
    if (report.places !== "ok") await step("places_hide", () => db.from("places").update({ is_hidden: true }).eq("user_id", uid));
  } else {
    await step("places", () => db.from("places").update({ is_hidden: true }).eq("user_id", uid));
  }

  await step("profiles", () => db.from("profiles").delete().eq("id", uid));
  console.log("[manage-user] wipe", uid, JSON.stringify(report));
  return report;
}
