// Base URL of the FastAPI backend. Configure with VITE_API_URL in frontend/.env.local (see .env.example).
export const BASE_URL = (import.meta.env?.VITE_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '');

/** Error carrying the backend's machine-readable code, e.g. INSUFFICIENT_FUNDS or MODEL_UNAVAILABLE. */
export class ApiError extends Error {
  constructor(message, { status = 0, code = 'NETWORK_ERROR', fields = [] } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

/** Turn any failed response body into a readable message (backend shape {error:{code,message}} or FastAPI {detail}). */
export function parseErrorBody(body, fallback) {
  if (body?.error?.message) {
    return { message: body.error.message, code: body.error.code ?? 'ERROR', fields: body.error.fields ?? [] };
  }
  if (typeof body?.detail === 'string') return { message: body.detail, code: 'ERROR', fields: [] };
  return { message: fallback, code: 'ERROR', fields: [] };
}

async function request(path, options = {}, fetchImpl = fetch) {
  let res;
  try {
    res = await fetchImpl(`${BASE_URL}${path}`, options);
  } catch {
    throw new ApiError(`Cannot reach the API at ${BASE_URL}. Is the backend running?`, { code: 'NETWORK_ERROR' });
  }
  if (!res.ok) {
    let body = null;
    try { body = await res.json(); } catch { /* non-JSON error body */ }
    const { message, code, fields } = parseErrorBody(body, res.statusText || `Request failed (${res.status})`);
    throw new ApiError(message, { status: res.status, code, fields });
  }
  return res.json();
}

export const getJson = (path, fetchImpl) => request(path, {}, fetchImpl);

export const postJson = (path, body, fetchImpl) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, fetchImpl);
