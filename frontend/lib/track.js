import { track as vercelTrack } from "@vercel/analytics";

// Thin wrapper so analytics never breaks the app (ad-blockers, local dev).
export function track(event, props) {
  try {
    vercelTrack(event, props);
  } catch {
    /* ignore */
  }
}