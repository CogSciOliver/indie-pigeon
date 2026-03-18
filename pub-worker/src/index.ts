/**
 * Welcome to Cloudflare Workers! This is your first worker.
 *
 * - Run `npm run dev` in your terminal to start a development server
 * - Open a browser tab at http://localhost:8787/ to see your worker in action
 * - Run `npm run deploy` to publish your worker
 *
 * Bind resources to your worker in `wrangler.jsonc`. After adding bindings, a type definition for the
 * `Env` object can be regenerated with `npm run cf-typegen`.
 *
 * Learn more at https://developers.cloudflare.com/workers/
 */

export interface Env {
  PRODUCTS: R2Bucket;
  DOWNLOAD_SECRET: string;
}

// hex encoding helper
function toHex(buffer: ArrayBuffer) {
  return [...new Uint8Array(buffer)].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function hmacSha256Hex(secret: string, message: string) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return toHex(sig);
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);

    // Health check
    if (url.pathname === "/" || url.pathname === "/health") {
      return new Response("OK", { status: 200 });
    }

    // IMPORTANT: disable the public /file route in production
    if (url.pathname.startsWith("/file/")) {
      return new Response("Disabled", { status: 403 });
    }

    // Secure download route
    if (url.pathname === "/dl") {
      const key = url.searchParams.get("key") || "";
      const expStr = url.searchParams.get("exp") || "";
      const sig = url.searchParams.get("sig") || "";

      if (!key || !expStr || !sig) return new Response("Missing params", { status: 400 });

      const exp = Number(expStr);
      if (!Number.isFinite(exp)) return new Response("Bad exp", { status: 400 });

      const now = Math.floor(Date.now() / 1000);
      if (now > exp) return new Response("Link expired", { status: 403 });

      // signature is HMAC(secret, `${key}.${exp}`)
      const message = `${key}.${exp}`;
      const expected = await hmacSha256Hex(env.DOWNLOAD_SECRET, message);

      // constant-time compare (simple)
      if (expected.length !== sig.length) return new Response("Bad signature", { status: 403 });
      let ok = 0;
      for (let i = 0; i < expected.length; i++) ok |= expected.charCodeAt(i) ^ sig.charCodeAt(i);
      if (ok !== 0) return new Response("Bad signature", { status: 403 });

      const obj = await env.PRODUCTS.get(key);
      if (!obj) return new Response("File not found", { status: 404 });

      const headers = new Headers();
      headers.set("Content-Type", obj.httpMetadata?.contentType || "application/pdf");
      headers.set("Content-Disposition", `attachment; filename="${key.split("/").pop() || "download"}"`);

      return new Response(obj.body, { headers });
    }

    return new Response("Not found", { status: 404 });
  },
};