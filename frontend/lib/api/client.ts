import type { ApiEnvelope } from "@/lib/types/api";

// CLAUDE.md Phase 0: two distinct API bases so the empty-frontend bug cannot recur.
// - On the SERVER (SSR, route handlers, Playwright/curl tooling) always use the internal
//   loopback URL — 127.0.0.1:8000 is always correct from inside the container.
// - In the BROWSER use the public forwarded Codespaces URL, which is what an external
//   browser must reach. NEXT_PUBLIC_ vars are inlined into the client bundle at build/dev.
const INTERNAL_BASE = process.env.API_BASE_URL_INTERNAL || "http://127.0.0.1:8000";
const PUBLIC_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || INTERNAL_BASE;
const API_BASE_URL = typeof window === "undefined" ? INTERNAL_BASE : PUBLIC_BASE;
export class ApiClient {
  constructor(private readonly baseUrl = API_BASE_URL) {}
  async get<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, { method: "GET", headers: { "Content-Type": "application/json" }, cache: "no-store" });
    return this.unwrap<T>(response);
  }
  async post<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store" });
    return this.unwrap<T>(response);
  }
  private async unwrap<T>(response: Response): Promise<T> {
    if (!response.ok) throw new Error(`API error ${response.status}: ${await response.text()}`);
    const payload = (await response.json()) as ApiEnvelope<T> | T;
    if (typeof payload === "object" && payload !== null && "success" in payload) {
      const envelope = payload as ApiEnvelope<T>;
      if (!envelope.success) throw new Error(envelope.error || envelope.message || "API returned failure");
      return envelope.data;
    }
    return payload as T;
  }
}
export const apiClient = new ApiClient();
