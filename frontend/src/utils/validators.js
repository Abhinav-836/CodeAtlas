// Accepts every GitHub URL format the backend accepts, plus the
// shorthand `user/repo`. Returns true on match.
export const isValidGitHubUrl = (url) => {
  if (!url || typeof url !== "string") return false;
  const patterns = [
    /^https?:\/\/github\.com\/[^/\s]+\/[^/\s#?]+(\/tree\/[^\s#?]+)?\/?$/,
    /^git@github\.com:[^/\s]+\/[^/\s]+\.git$/,
    /^gh repo clone [^/\s]+\/[^/\s]+$/,
    /^[^/\s]+\/[^/\s]+$/, // user/repo shorthand
  ];
  return patterns.some((p) => p.test(url.trim()));
};

export const isValidZipFile = (file) => {
  if (!file) return false;
  const allowedTypes = [
    "application/zip",
    "application/x-zip-compressed",
    "multipart/x-zip",
  ];
  const isZipType = allowedTypes.includes(file.type);
  const isZipExtension = file.name.toLowerCase().endsWith(".zip");
  return isZipType || isZipExtension;
};

export const validateFileSize = (file, maxSizeMB = 100) => {
  if (!file) return false;
  return file.size <= maxSizeMB * 1024 * 1024;
};

export const validateAnalysisStatus = (status) => {
  const valid = [
    "idle",
    "queued",
    "pending",
    "running",
    "processing",
    "extracting",
    "scanning",
    "analyzing",
    "generating_report",
    "completed",
    "failed",
    "timeout",
    "cancelled",
  ];
  return valid.includes(status);
};