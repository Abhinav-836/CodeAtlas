import axios from "axios";
import { API_URL } from "./constants";

const api = axios.create({ baseURL: API_URL });

/* -------------------- UPLOAD API -------------------- */
export const uploadAPI = {
  uploadZip: (formData) =>
    api.post("/api/upload/zip", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  // Don't force a branch - the backend auto-detects it. Only pass one
  // if the caller explicitly provides it.
  uploadGithub: (repoUrl, branch) => {
    const params = new URLSearchParams({ repo_url: repoUrl });
    if (branch) params.set("branch", branch);
    return api.post(`/api/upload/github?${params.toString()}`);
  },

  listUploads: () => api.get("/api/upload/uploads"),
};

/* -------------------- ANALYZE API -------------------- */
export const analyzeAPI = {
  analyzeRepository: (path) =>
    api.post(`/api/analyze?path=${encodeURIComponent(path)}`),

  startAnalysis: (path) =>
    api.post(`/api/analyze?path=${encodeURIComponent(path)}`),

  getStatus: (taskId) => api.get(`/api/analyze/status/${taskId}`),

  getResults: (taskId, includeAI = false) =>
    api.get(
      `/api/analyze/results/${taskId}${includeAI ? "?include_ai=true" : ""}`
    ),
};

/* -------------------- REPORTS API -------------------- */
export const reportsAPI = {
  listReports: () => api.get("/api/reports"),

  getReport: (reportId, format = "json", download = false) =>
    api.get(
      `/api/reports/${reportId}?format=${format}&download=${download}`
    ),

  getReportSummary: (reportId) => api.get(`/api/reports/${reportId}/summary`),

  deleteReport: (reportId) => api.delete(`/api/reports/${reportId}`),

  searchReports: (query) =>
    api.get(`/api/reports/search?query=${encodeURIComponent(query)}`),

  // Creates a temp export on the server and returns { download_url }.
  // Caller must prepend /api to download_url (the router returns paths
  // relative to itself).
  exportReport: (reportId, format = "json") =>
    api.post(`/api/reports/${reportId}/export?format=${format}`),

  // Direct in-browser download that doesn't create a temp file on the server.
  downloadReportUrl: (reportId, format = "json") =>
    `${API_URL}/api/reports/${reportId}?format=${format}&download=true`,
};

export default api;