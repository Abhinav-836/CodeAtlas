/*
 * Per-browser owner token. CodeAtlas has no accounts: each browser gets a
 * random secret on first load, sent as X-Owner-Token on every request, and
 * the server only shows what was created with it. Never put it in a URL.
 */
const STORAGE_KEY = "codeatlas_owner_token";
const VALID = /^[A-Za-z0-9_-]{32,128}$/;

let memoryToken = null; // fallback when storage is blocked

const generate = () => {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  const bytes = new Uint8Array(24);
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
};

export function getOwnerToken() {
  if (typeof window === "undefined") return "";
  try {
    let token = window.localStorage.getItem(STORAGE_KEY);
    if (!token || !VALID.test(token)) {
      token = generate();
      window.localStorage.setItem(STORAGE_KEY, token);
    }
    return token;
  } catch {
    if (!memoryToken) memoryToken = generate();
    return memoryToken;
  }
}