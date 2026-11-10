export const MAX_FILE_SIZE_MB = 100;

// Every GitHub URL format the backend accepts, plus `user/repo` shorthand.
export const isValidGitHubUrl = (url) => {
  if (!url || typeof url !== "string") return false;
  const patterns = [
    // With or without https:// and www. (the form's own example is github.com/owner/repo)
    /^(https?:\/\/)?(www\.)?github\.com\/[^/\s]+\/[^/\s#?]+(\/tree\/[^\s#?]+)?\/?$/i,
    /^git@github\.com:[^/\s]+\/[^/\s]+\.git$/,
    /^gh repo clone [^/\s]+\/[^/\s]+$/,
    // owner/repo shorthand (but not "github.com/owner", which is missing the repo)
    /^(?!(www\.)?github\.com\/)[^/\s]+\/[^/\s]+$/i,
  ];
  return patterns.some((p) => p.test(url.trim()));
};

export const isValidZipFile = (file) => {
  if (!file) return false;
  const types = ["application/zip", "application/x-zip-compressed", "multipart/x-zip"];
  return types.includes(file.type) || file.name.toLowerCase().endsWith(".zip");
};

export const isWithinSize = (file, maxMB = MAX_FILE_SIZE_MB) => Boolean(file) && file.size <= maxMB * 1024 * 1024;