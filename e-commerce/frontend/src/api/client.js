export const API_BASE = "/api/v1";
export const DEFAULT_WAREHOUSE = "00000000-0000-0000-0000-000000000001";

/**
 * Low-level fetch wrapper.
 * Attaches Authorization header when token is provided.
 * Handles 401 (session expired) and 403 (forbidden).
 */
export async function httpRequest(path, { token, onUnauthorized, ...options } = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    onUnauthorized?.();
    throw new Error("Sessione scaduta");
  }

  if (res.status === 403) {
    throw new Error("Accesso negato");
  }

  if (res.status === 204) return null;

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || body.error || `Errore ${res.status}`);
  }

  return res.json();
}
