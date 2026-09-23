import { useEffect, useState, useCallback, useRef } from "react";
import { analyzeAPI } from "../utils/apiClient";

const PROGRESS_MAP = {
  idle: 0,
  queued: 10,
  pending: 15,
  running: 45,
  processing: 30,
  extracting: 25,
  scanning: 50,
  analyzing: 60,
  generating_report: 80,
  completed: 100,
  failed: 0,
  timeout: 0,
  cancelled: 0,
};

export function useAnalysis(taskId) {
  const [status, setStatus] = useState("idle");
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const pollingRef = useRef(null);
  const hasFetchedResults = useRef(false);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const fetchResults = useCallback(async () => {
    if (!taskId || hasFetchedResults.current) return;
    try {
      const response = await analyzeAPI.getResults(taskId, true);
      if (!isMountedRef.current) return;
      setResults(response.data);
      hasFetchedResults.current = true;
      setProgress(100);
    } catch (err) {
      if (!isMountedRef.current) return;
      setError(err.response?.data?.detail || "Failed to fetch results");
    }
  }, [taskId]);

  const fetchStatus = useCallback(async () => {
    if (!taskId) return;
    try {
      setLoading(true);
      const response = await analyzeAPI.getStatus(taskId);
      if (!isMountedRef.current) return;

      const data = response.data;
      setStatus(data.status);
      setProgress(PROGRESS_MAP[data.status] ?? 0);

      if (data.status === "completed" && !hasFetchedResults.current) {
        stopPolling();
        await fetchResults();
      } else if (
        data.status === "failed" ||
        data.status === "timeout" ||
        data.status === "cancelled"
      ) {
        stopPolling();
        setError(data.error || `Analysis ${data.status}`);
      }
    } catch (err) {
      if (!isMountedRef.current) return;
      setError(err.response?.data?.detail || "Failed to fetch analysis status");
    } finally {
      if (isMountedRef.current) setLoading(false);
    }
  }, [taskId, fetchResults, stopPolling]);

  useEffect(() => {
    if (!taskId) {
      setStatus("idle");
      setProgress(0);
      setResults(null);
      setError(null);
      hasFetchedResults.current = false;
      return;
    }

    hasFetchedResults.current = false;
    fetchStatus();
    pollingRef.current = setInterval(fetchStatus, 2000);

    return () => {
      stopPolling();
    };
  }, [taskId, fetchStatus, stopPolling]);

  return { status, progress, results, error, loading };
}