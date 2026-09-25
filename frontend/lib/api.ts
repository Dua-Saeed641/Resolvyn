/**
 * Thin fetch wrapper over the backend (../backend, docs/architecture.md §3
 * tech stack). All data-fetching must go through here so the base URL and
 * error handling stay in one place.
 */

// Same-origin by default (Next proxies /api and /ws to the backend, see next.config.mjs), so the app works unchanged on
// localhost, on a phone, and behind a tunnel. NEXT_PUBLIC_API_BASE_URL can still point at a different backend.
const explicit = process.env.NEXT_PUBLIC_API_BASE_URL;
const origin = typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:3000";
export const API_BASE_URL = explicit || `${origin}/api`;
const ORIGIN = API_BASE_URL.replace(/\/api\/?$/, "");
export const WS_BASE_URL = ORIGIN.replace(/^http/, "ws");

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: isForm ? init?.headers : { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = `Request to ${path} failed with ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
};

export function ttsUrl(text: string, lang: string): string {
  return `${API_BASE_URL}/tts?lang=${encodeURIComponent(lang)}&text=${encodeURIComponent(text)}`;
}
