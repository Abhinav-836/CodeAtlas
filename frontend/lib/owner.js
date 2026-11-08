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
/** Is this a key copied from another browser? Same rule as the server. */
export const isValidKey = (key) => VALID.test(String(key || "").trim());

/** Switch this browser to another browser's key, so both see the same reports. */
export function setOwnerToken(token) {
  const value = String(token || "").trim();
  if (!VALID.test(value)) throw new Error("That key isn't valid.");
  memoryToken = value;
  try {
    window.localStorage.setItem(STORAGE_KEY, value);
  } catch {
    /* storage blocked: the memory copy lasts until the tab closes */
  }
}
