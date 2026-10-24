import { useEffect, useState, useCallback, useRef } from "react";
import { analyzeAPI } from "../utils/apiClient";
import { POLLING_INTERVAL } from "../utils/constants";

const PROGRESS_MAP = {
  idle: 0, queued: 10, pending: 15, running: 45, processing: 30,
  extracting: 25, scanning: 50, analyzing: 60, generating_report: 80,
  completed: 100, failed: 0, timeout: 0, cancelled: 0,
};

const TERMINAL_FAILURES = new Set(["failed", "timeout", "cancelled"]);

const errorMessage = (err, fallback) =>
  err?.response?.data?.detail ||
  (err?.code === "ERR_NETWORK"
    ? "Cannot reach the CodeAtlas server. It may be waking up - try again in a minute."
    : err?.message) ||
  fallback;

export function useAnalysis(taskId) {
  const [status, setStatus] = useState("idle");
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const pollingRef = useRef(null);
  const hasFetchedResults = useRef(false);
  const isMountedRef = useRef(true);
  const networkFailures = useRef(0);

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
    hasFetchedResults.current = true; // prevent duplicate concurrent fetches
    try {
      const response = await analyzeAPI.getResults(taskId, true);
      if (!isMountedRef.current) return;
      setResults(response.data);
      setProgress(100);
    } catch (err) {
      if (!isMountedRef.current) return;
      setError(errorMessage(err, "Failed to fetch results"));
    }
  }, [taskId]);

  const fetchStatus = useCallback(async () => {
    if (!taskId) return;
    try {
      setLoading(true);
      const { data } = await analyzeAPI.getStatus(taskId);
      if (!isMountedRef.current) return;
      networkFailures.current = 0;

      setStatus(data.status);
      setProgress(PROGRESS_MAP[data.status] ?? 0);

      if (data.status === "completed") {
        stopPolling();
        await fetchResults();
      } else if (TERMINAL_FAILURES.has(data.status)) {
        stopPolling();
        setError(data.error || `Analysis ${data.status}`);
      }
    } catch (err) {
      if (!isMountedRef.current) return;
      // 404 = task unknown to the server (restart / cleanup). Polling it
      // every 2s forever, as before, can never succeed.
      if (err?.response?.status === 404) {
        stopPolling();
        setStatus("failed");
        setError(errorMessage(err, "This analysis is no longer available."));
        return;
      }
      // Tolerate a few transient network blips (Render cold starts).
      networkFailures.current += 1;
      if (networkFailures.current >= 5) {
        stopPolling();
        setStatus("failed");
        setError(errorMessage(err, "Failed to fetch analysis status"));
      }
    } finally {
      if (isMountedRef.current) setLoading(false);
    }
  }, [taskId, fetchResults, stopPolling]);

  useEffect(() => {
    setStatus(taskId ? "queued" : "idle");
    setProgress(0);
    setResults(null);
    setError(null);
    hasFetchedResults.current = false;
    networkFailures.current = 0;

    if (!taskId) return;

    fetchStatus();
    pollingRef.current = setInterval(fetchStatus, POLLING_INTERVAL);
    return () => stopPolling();
  }, [taskId, fetchStatus, stopPolling]);

  return { status, progress, results, error, loading };
}