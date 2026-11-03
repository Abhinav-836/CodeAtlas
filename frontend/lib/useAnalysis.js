"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { analyzeAPI, errorMessage } from "./api";

const POLL_MS = 2000;
const TERMINAL_FAILURES = new Set(["failed", "timeout", "cancelled"]);

// Ordered stages shown on the progress screen. Backend statuses map onto them.
export const STAGES = [
  { key: "queued", label: "Queued", statuses: ["idle", "queued", "pending"] },
  { key: "extract", label: "Reading files", statuses: ["extracting", "processing"] },
  { key: "scan", label: "Scanning for secrets & risky patterns", statuses: ["scanning", "running"] },
  { key: "analyze", label: "Measuring complexity", statuses: ["analyzing"] },
  { key: "report", label: "Writing the report", statuses: ["generating_report"] },
];

export const stageIndex = (status) => {
  if (status === "completed") return STAGES.length;
  const i = STAGES.findIndex((s) => s.statuses.includes(status));
  return i === -1 ? 0 : i;
};

export function useAnalysis(taskId) {
  const [status, setStatus] = useState(taskId ? "queued" : "idle");
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const timer = useRef(null);
  const fetchedResults = useRef(false);
  const alive = useRef(true);
  const netFailures = useRef(0);

  const stop = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  }, []);

  const fetchResults = useCallback(async () => {
    if (fetchedResults.current) return;
    fetchedResults.current = true;
    try {
      const { data } = await analyzeAPI.results(taskId);
      if (alive.current) setResults(data);
    } catch (err) {
      if (alive.current) setError(errorMessage(err, "Couldn't load the results."));
    }
  }, [taskId]);

  const poll = useCallback(async () => {
    try {
      const { data } = await analyzeAPI.status(taskId);
      if (!alive.current) return;
      netFailures.current = 0;
      setStatus(data.status);
      if (data.status === "completed") {
        stop();
        await fetchResults();
      } else if (TERMINAL_FAILURES.has(data.status)) {
        stop();
        setError(data.error || `The analysis ${data.status === "timeout" ? "timed out" : data.status}.`);
      }
    } catch (err) {
      if (!alive.current) return;
      // 404 = task unknown to the server (restart / cleanup); polling can't recover.
      if (err?.response?.status === 404) {
        stop();
        setStatus("gone");
        setError("This analysis is no longer on the server — it was likely cleared when the server restarted.");
        return;
      }
      // Tolerate a few blips while Render wakes up.
      netFailures.current += 1;
      if (netFailures.current >= 5) {
        stop();
        setStatus("failed");
        setError(errorMessage(err, "Lost contact with the analysis server."));
      }
    }
  }, [taskId, fetchResults, stop]);

  useEffect(() => {
    alive.current = true;
    fetchedResults.current = false;
    netFailures.current = 0;
    setResults(null);
    setError(null);
    setStatus(taskId ? "queued" : "idle");
    if (!taskId) return undefined;
    poll();
    timer.current = setInterval(poll, POLL_MS);
    return () => {
      alive.current = false;
      stop();
    };
  }, [taskId, poll, stop]);

  return { status, results, error };
}