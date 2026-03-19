import { useCallback } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { httpRequest } from "../api/client.js";

/**
 * Hook that returns get / post / put / del helpers
 * pre-configured with the current JWT token.
 */
export function useApi() {
  const { user, logout } = useAuth();

  const request = useCallback(
    (path, options = {}) =>
      httpRequest(path, {
        ...options,
        token: user?.token,
        onUnauthorized: logout,
      }),
    [user, logout],
  );

  const get = useCallback((path) => request(path), [request]);

  const post = useCallback(
    (path, body) =>
      request(path, { method: "POST", body: JSON.stringify(body) }),
    [request],
  );

  const put = useCallback(
    (path, body) =>
      request(path, {
        method: "PUT",
        body: body ? JSON.stringify(body) : undefined,
      }),
    [request],
  );

  const del = useCallback(
    (path) => request(path, { method: "DELETE" }),
    [request],
  );

  return { get, post, put, del };
}
