import { useState } from "react";
import { uploadAPI, analyzeAPI } from "../utils/apiClient";

export function useUpload() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);

  const uploadFile = async (file) => {
    setLoading(true);
    setError(null);
    setProgress(0);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + 10;
        });
      }, 300);

      const formData = new FormData();
      formData.append("file", file);

      const uploadResponse = await uploadAPI.uploadZip(formData);

      clearInterval(progressInterval);
      setProgress(100);

      return uploadResponse.data.path;
    } catch (err) {
      setError(err?.message || "Upload failed");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const uploadFromGithub = async (url) => {
    setLoading(true);
    setError(null);

    try {
      // ✅ Fixed: send repoUrl directly (not as object)
      const response = await uploadAPI.uploadGithub(url);
      return response.data.path;
    } catch (err) {
      setError(err?.message || "GitHub upload failed");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // ✅ Fixed: use analyzeAPI.startAnalysis (which encodes path)
  const startAnalysis = async (path) => {
    setLoading(true);
    setError(null);

    try {
      const response = await analyzeAPI.startAnalysis(path);
      return response.data.task_id;
    } catch (err) {
      setError(err?.message || "Analysis failed to start");
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
      setError(err?.message || "Failed to fetch uploads");
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