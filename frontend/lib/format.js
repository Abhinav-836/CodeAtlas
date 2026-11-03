export const fileName = (p) => p?.split(/[\\/]/).pop() ?? "";

// Upload/clone folders end in _<8 hex>; strip it for display.
export const repoDisplayName = (r) =>
  (r?.repo_name || fileName(r?.path) || r?.id || "Untitled repository").replace(/_[0-9a-f]{8}$/, "");

export const formatDate = (date) => {
  if (!date) return "—";
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return String(date);
  return d.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
};

export const humanSize = (bytes) => {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let n = bytes;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(n >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
};

export const SEVERITIES = ["critical", "high", "medium", "low"];

export const normalizeLevel = (level) => {
  const l = String(level || "none").toLowerCase();
  return ["critical", "high", "medium", "low"].includes(l) ? l : "none";
};