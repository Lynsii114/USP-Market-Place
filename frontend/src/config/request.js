// Keep credentials in memory: a page refresh requires signing in again.
import { API_URL } from "./api";

let accessToken = null;

export function setAccessToken(token) {
  accessToken = token || null;
}

export function apiFetch(input, options = {}) {
  const url = new URL(input, window.location.origin);
  const api = new URL(API_URL, window.location.origin);
  const headers = new Headers(options.headers);
  if (accessToken && url.origin === api.origin && (url.pathname === api.pathname || url.pathname.startsWith(`${api.pathname}/`))) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  return window.fetch(input, { ...options, headers });
}
