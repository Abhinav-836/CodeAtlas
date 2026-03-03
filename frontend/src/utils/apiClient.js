import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
});

/* -------------------- UPLOAD API -------------------- */
export const uploadAPI = {
  uploadZip: (formData) =>
    api.post("/api/upload/zip", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  // FIXED: Send repo_url as query parameter, not in body
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