import axios from "axios";
import { getOwnerToken } from "./owner";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

const api = axios.create({ baseURL: API_URL });

// Every request carries this browser's owner token. The backend rejects
// requests without it (401) and only returns your own uploads/reports.
api.interceptors.request.use((config) => {
  config.headers = config.headers ?? {};
  config.headers["X-Owner-Token"] = getOwnerToken();
  return config;
});

// With responseType "blob", error bodies arrive as a Blob, so
// err.response.data.detail is undefined. Parse JSON error blobs back.
api.interceptors.response.use(undefined, async (error) => {
  const data = error?.response?.data;
  if (typeof Blob !== "undefined" && data instanceof Blob && data.type.includes("json")) {
    try {
      error.response.data = JSON.parse(await data.text());
    } catch {
      /* keep original */
    }
  }
  return Promise.reject(error);
});

export function errorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (err?.code === "ERR_NETWORK") {
    return "The analysis server isn't answering. It sleeps when idle and takes about a minute to wake — try again shortly.";
  }
  return err?.message || fallback;
}

const saveBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

const filenameFrom = (headers, fallback) => {
  const match = /filename="?([^";]+)"?/i.exec(headers?.["content-disposition"] || "");
  return match ? match[1] : fallback;
};

export const uploadAPI = {
  uploadZip: (file, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/api/upload/zip", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
      },
    });
  },
  // Branch is optional — the backend auto-detects the default branch.
  uploadGithub: (repoUrl, branch) => {
    const params = new URLSearchParams({ repo_url: repoUrl });
    if (branch) params.set("branch", branch);
    return api.post(`/api/upload/github?${params.toString()}`);
  },
};

export const analyzeAPI = {
  start: (path) => api.post(`/api/analyze?path=${encodeURIComponent(path)}`),
  status: (taskId) => api.get(`/api/analyze/status/${encodeURIComponent(taskId)}`),
  results: (taskId) => api.get(`/api/analyze/results/${encodeURIComponent(taskId)}?include_ai=true`),
};

const EXTENSIONS = { json: "json", html: "html", markdown: "md", pdf: "pdf" };

export const reportsAPI = {
  list: () => api.get("/api/reports"),
  summary: (id) => api.get(`/api/reports/${encodeURIComponent(id)}/summary`),
  remove: (id) => api.delete(`/api/reports/${encodeURIComponent(id)}`),
  search: (q) => api.get(`/api/reports/search?query=${encodeURIComponent(q)}`),
  // Downloads through axios so the owner header is sent; a plain link can't.
  download: async (id, format = "json") => {
    const res = await api.get(`/api/reports/${encodeURIComponent(id)}`, {
      params: { format, download: true },
      responseType: "blob",
    });
    saveBlob(res.data, filenameFrom(res.headers, `codeatlas-report.${EXTENSIONS[format] || format}`));
  },
};

export default api;