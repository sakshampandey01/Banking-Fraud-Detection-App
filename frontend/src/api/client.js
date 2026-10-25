// Vite replaces import.meta.env at build time. VITE_USE_MOCK defaults to true so the UI runs without a backend.
export const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
export const USE_MOCK = true;

/** GET json. Handles both of the backend's error shapes: {error:{message}} and FastAPI's {detail}. */
export async function getJson(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.error?.message ?? (typeof body.detail === 'string' ? body.detail : message);
    } catch { /* non-JSON error body */ }
    throw new Error(message || `Request failed (${res.status})`);
  }
  return res.json();
}
