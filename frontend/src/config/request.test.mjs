import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

// Supply the Vite-configured URL while testing the actual request wrapper in Node.
const source = (await readFile(new URL("./request.js", import.meta.url), "utf8"))
  .replace('import { API_URL } from "./api";', 'const API_URL = "http://localhost:8000/api";');
const { apiFetch, setAccessToken } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
const events = [];
globalThis.window = {
  location: { origin: "http://localhost:5173" },
  dispatchEvent: (event) => events.push(event),
};
const endpoint = "http://localhost:8000/api/users/session";

test("suspension ends a session once and preserves the response for callers", async () => {
  events.length = 0;
  setAccessToken("student-token");
  window.fetch = async (_input, options) => {
    assert.equal(options.headers.get("Authorization"), "Bearer student-token");
    return Response.json({ code: "account_suspended", detail: "Suspended until tomorrow. Please check your email." }, { status: 403 });
  };
  const response = await apiFetch(endpoint);
  assert.equal((await response.json()).code, "account_suspended");
  assert.equal(events.length, 1);
  assert.match(events[0].detail.message, /signed out.*Suspended until tomorrow/);
  window.fetch = async (_input, options) => {
    assert.equal(options.headers.has("Authorization"), false);
    return Response.json({ status: "ok" });
  };
  await apiFetch(endpoint);
});

test("ordinary permission errors do not sign out a valid session", async () => {
  events.length = 0;
  setAccessToken("student-token");
  window.fetch = async () => Response.json({ detail: "Admin access required" }, { status: 403 });
  await apiFetch(endpoint);
  assert.equal(events.length, 0);
});

test("an expired session clears credentials and requests sign-in", async () => {
  events.length = 0;
  setAccessToken("expired-token");
  window.fetch = async () => Response.json({ detail: "Please sign in again" }, { status: 401 });
  await apiFetch(endpoint);
  assert.equal(events.length, 1);
  assert.match(events[0].detail.message, /Please sign in again/);
});

test("a delayed rejection cannot end a newly signed-in session", async () => {
  events.length = 0;
  setAccessToken("old-token");
  let finish;
  window.fetch = () => new Promise((resolve) => { finish = resolve; });
  const pending = apiFetch(endpoint);
  setAccessToken("new-token");
  finish(Response.json({ code: "account_suspended", detail: "Suspended" }, { status: 403 }));
  await pending;
  assert.equal(events.length, 0);
});
