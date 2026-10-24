import axios from "axios";
import { API_URL } from "./constants";
import { getOwnerToken } from "./owner";

const api = axios.create({ baseURL: API_URL });

// Every request carries this browser's owner token. The backend rejects
// requests without it (401) and only returns your own uploads/reports.
api.interceptors.request.use((config) => {
  config.headers = config.headers ?? {};
  config.headers["X-Owner-Token"] = getOwnerToken();
  return config;
});

// Fetch a file through axios (so the owner header is sent) and hand it to
// the browser as a download. A plain <a href> or window.open() can't send
// headers, and putting the token in the URL would leak it into logs.
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

/* -------------------- UPLOAD API -------------------- */
export const uploadAPI = {
  uploadZip: (formData) =>
    api.post("/api/upload/zip", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  // Don't force a branch - the backend auto-detects it.
  uploadGithub: (repoUrl, branch) => {
    const params = new URLSearchParams({ repo_url: repoUrl });
    if (branch) params.set("branch", branch);
    return api.post(`/api/upload/github?${params.toString()}`);
  },

  listUploads: () => api.get("/api/upload/uploads"),
};

/* -------------------- ANALYZE API -------------------- */
export const analyzeAPI = {
  startAnalysis: (path) =>
    api.post(`/api/analyze?path=${encodeURIComponent(path)}`),

  getStatus: (taskId) => api.get(`/api/analyze/status/${encodeURIComponent(taskId)}`),

  getResults: (taskId, includeAI = false) =>
    api.get(
      `/api/analyze/results/${encodeURIComponent(taskId)}${includeAI ? "?include_ai=true" : ""}`
    ),
};

/* -------------------- REPORTS API -------------------- */
const EXTENSIONS = { json: "json", html: "html", markdown: "md", pdf: "pdf" };

export const reportsAPI = {
  listReports: () => api.get("/api/reports"),

  getReportSummary: (reportId) =>
    api.get(`/api/reports/${encodeURIComponent(reportId)}/summary`),

  deleteReport: (reportId) => api.delete(`/api/reports/${encodeURIComponent(reportId)}`),

  searchReports: (query) =>
    api.get(`/api/reports/search?query=${encodeURIComponent(query)}`),

  // Downloads the report in the given format (json, html, markdown, pdf).
  downloadReport: async (reportId, format = "json") => {
    const response = await api.get(`/api/reports/${encodeURIComponent(reportId)}`, {
      params: { format, download: true },
      responseType: "blob",
    });
    const fallback = `codeatlas-report.${EXTENSIONS[format] || format}`;
    saveBlob(response.data, filenameFrom(response.headers, fallback));
  },
};

/*
 * With responseType "blob", error bodies arrive as a Blob too, so
 * err.response.data.detail is undefined. Turn JSON error blobs back into
 * objects so the UI can show the server's message.
 */
api.interceptors.response.use(undefined, async (error) => {
  const data = error?.response?.data;
  if (data instanceof Blob && data.type.includes("json")) {
    try {
      error.response.data = JSON.parse(await data.text());
    } catch {
      /* keep original */
    }
  }
  return Promise.reject(error);
});

export default api;