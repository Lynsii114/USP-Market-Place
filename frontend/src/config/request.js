// Keep credentials in memory: a page refresh requires signing in again.
import { API_URL } from "./api";

let accessToken = null;

export function setAccessToken(token) {
  accessToken = token || null;
}

export async function apiFetch(input, options = {}) {
  const url = new URL(input, window.location.origin);
  const api = new URL(API_URL, window.location.origin);
  const headers = new Headers(options.headers);
  const requestToken = accessToken;
  const authenticated = requestToken && url.origin === api.origin && (url.pathname === api.pathname || url.pathname.startsWith(`${api.pathname}/`));
  if (authenticated) {
    headers.set("Authorization", `Bearer ${requestToken}`);
  }
  const response = await window.fetch(input, { ...options, headers });
  if (authenticated && (response.status === 401 || response.status === 403)) {
    const data = await response.clone().json().catch(() => null);
    if (accessToken === requestToken && (response.status === 401 || data?.code === "account_suspended")) {
      setAccessToken(null);
      window.dispatchEvent(new CustomEvent("marketplace-session-ended", {
        detail: { message: data?.code === "account_suspended"
          ? `You have been signed out. ${data.detail}`
          : "Your session has ended. Please sign in again." },
      }));
    }
  }
  return response;
}
