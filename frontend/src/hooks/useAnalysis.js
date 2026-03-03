import { useEffect, useState, useCallback, useRef } from "react";
import { analyzeAPI } from "../utils/apiClient";

export function useAnalysis(taskId) {
  const [status, setStatus] = useState("idle");
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const pollingRef = useRef(null);
  const hasFetchedResults = useRef(false);

  // Calculate progress based on status
  const getProgressFromStatus = (status) => {
    const progressMap = {
      'queued': 10,
      'pending': 15,
      'processing': 30,
      'extracting': 25,
      'scanning': 50,
      'analyzing': 60,
      'generating_report': 80,
      'running': 45,
      'completed': 100,
      'failed': 0,
      'timeout': 0,
      'cancelled': 0
    };
    return progressMap[status] || 0;
  };

  const fetchStatus = useCallback(async () => {
    if (!taskId) return;

    try {
      setLoading(true);
      const response = await analyzeAPI.getStatus(taskId);
      const data = response.data;
      
      console.log("Status update:", data); // Debug log
      
      setStatus(data.status);
      setProgress(getProgressFromStatus(data.status));

      if (data.status === "completed" && !hasFetchedResults.current) {
        // Clear polling when completed
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        // Fetch results
        await fetchResults();
      } else if (data.status === "failed") {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        setError(data.error || "Analysis failed");
      }
    } catch (err) {
      console.error("Status fetch error:", err);
      // Don't clear polling on error, just log it
      setError(err.response?.data?.detail || "Failed to fetch analysis status");
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  const fetchResults = useCallback(async () => {
    if (!taskId || hasFetchedResults.current) return;
  
    try {
      console.log("Fetching results for task:", taskId);
      // ✅ Request AI insights by passing true
      const response = await analyzeAPI.getResults(taskId, true);
      console.log("Results received:", response.data);
      setResults(response.data);
      hasFetchedResults.current = true;
      setProgress(100);
    } catch (err) {
      console.error("Results fetch error:", err);
      setError(err.response?.data?.detail || "Failed to fetch results");
    }
  }, [taskId]);

  // Start polling when taskId changes
  useEffect(() => {
    if (!taskId) {
      setStatus("idle");
      setProgress(0);
      setResults(null);
      setError(null);
      hasFetchedResults.current = false;
      return;
    }

    console.log("Starting analysis for task:", taskId);
    
    // Initial fetch
    fetchStatus();

    // Set up polling
    pollingRef.current = setInterval(() => {
      fetchStatus();
    }, 2000);

    // Cleanup on unmount or taskId change
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [taskId, fetchStatus]);

  return {
    status,
    progress,
    results,
    error,
    loading,
  };
}