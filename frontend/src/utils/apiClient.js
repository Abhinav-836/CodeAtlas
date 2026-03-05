import axios from "axios";

// Use environment variable with fallback
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
});

/* -------------------- UPLOAD API -------------------- */
export const uploadAPI = {
  uploadZip: (formData) =>
    api.post("/api/upload/zip", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  uploadGithub: (repoUrl, branch = "main") =>
    api.post(`/api/upload/github?repo_url=${encodeURIComponent(repoUrl)}&branch=${encodeURIComponent(branch)}`),

  listUploads: () => api.get("/api/upload/uploads"),
};

/* -------------------- ANALYZE API -------------------- */
export const analyzeAPI = {
  analyzeRepository: (path) =>
    api.post(`/api/analyze?path=${encodeURIComponent(path)}`),

  startAnalysis: (path) =>
    api.post(`/api/analyze?path=${encodeURIComponent(path)}`),

  getStatus: (taskId) =>
    api.get(`/api/analyze/status/${taskId}`),

  getResults: (taskId, includeAI = false) =>
    api.get(`/api/analyze/results/${taskId}${includeAI ? '?include_ai=true' : ''}`),
};

/* -------------------- REPORTS API -------------------- */
export const reportsAPI = {
  listReports: () => api.get("/api/reports"),

  getReport: (reportId) =>
    api.get(`/api/reports/${reportId}`),

  deleteReport: (reportId) =>
    api.delete(`/api/reports/${reportId}`),

  searchReports: (query) =>
    api.get(`/api/reports/search?q=${query}`),

  exportReport: (reportId, format) =>
    api.get(`/api/reports/${reportId}/export?format=${format}`),
};
