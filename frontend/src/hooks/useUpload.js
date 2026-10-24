import { useState } from "react";
import { uploadAPI, analyzeAPI } from "../utils/apiClient";

// Prefer the backend's explanation ("File too large inside ZIP: ...")
// over axios' generic "Request failed with status code 400".
const errorMessage = (err, fallback) =>
  err?.response?.data?.detail ||
  (err?.code === "ERR_NETWORK"
    ? "Cannot reach the CodeAtlas server. It may be waking up - please retry in a minute."
    : err?.message) ||
  fallback;

export function useUpload() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);

  const uploadFile = async (file) => {
    setLoading(true);
    setError(null);
    setProgress(0);

    // Declared outside try so it is ALWAYS cleared. Previously a failed
    // upload skipped clearInterval and the timer kept running forever.
    const progressInterval = setInterval(() => {
      setProgress((prev) => (prev >= 90 ? prev : prev + 10));
    }, 300);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const uploadResponse = await uploadAPI.uploadZip(formData);
      setProgress(100);

      // Backend returns "extracted_to" for ZIP uploads.
      return uploadResponse.data.extracted_to;
    } catch (err) {
      setProgress(0);
      setError(errorMessage(err, "Upload failed"));
      throw err;
    } finally {
      clearInterval(progressInterval);
      setLoading(false);
    }
  };

  const uploadFromGithub = async (url, branch = null) => {
    setLoading(true);
    setError(null);
    try {
      // Let the backend auto-detect the branch if none is given.
      const response = await uploadAPI.uploadGithub(url.trim(), branch);
      return response.data.local_path;
    } catch (err) {
      setError(errorMessage(err, "GitHub upload failed"));
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const startAnalysis = async (path) => {
    setLoading(true);
    setError(null);
    try {
      const response = await analyzeAPI.startAnalysis(path);
      return response.data.task_id;
    } catch (err) {
      setError(errorMessage(err, "Analysis failed to start"));
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const getUploads = async () => {
    try {
      const response = await uploadAPI.listUploads();
      return response.data.uploads || [];
    } catch (err) {
      setError(errorMessage(err, "Failed to fetch uploads"));
      throw err;
    }
  };

  return {
    loading,
    error,
    progress,
    uploadFile,
    uploadFromGithub,
    startAnalysis,
    getUploads,
    clearError: () => setError(null),
  };
}