/*
 * Per-browser owner token.
 *
 * CodeAtlas has no accounts. Each browser gets a random secret the first
 * time it loads the app; every API request sends it in X-Owner-Token and
 * the server only lets you see / download / delete what you created with it.
 *
 * It lives in localStorage, so it survives reloads and restarts. Clearing
 * site data or switching browser means starting fresh - like an anonymous
 * session. Never put this token in a URL: URLs end up in logs and history.
 */
const STORAGE_KEY = "codeatlas_owner_token";
const VALID = /^[A-Za-z0-9_-]{32,128}$/;

let memoryToken = null; // fallback when storage is blocked (private mode etc.)

const generate = () => {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  const bytes = new Uint8Array(24);
  window.crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
};

export function getOwnerToken() {
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