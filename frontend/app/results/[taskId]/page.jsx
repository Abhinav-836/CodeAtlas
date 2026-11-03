"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useAnalysis } from "@/lib/useAnalysis";
import { track } from "@/lib/track";
import AnalysisProgress from "@/components/AnalysisProgress";
import ResultsView from "@/components/ResultsView";

export default function ResultsPage() {
  const params = useParams();
  const taskId = decodeURIComponent(String(params?.taskId || ""));
  const { status, results, error } = useAnalysis(taskId);
  const tracked = useRef(false);

  useEffect(() => {
    if (results && !tracked.current) {
      tracked.current = true;
      track("analysis_viewed", { risk: results.overall_risk_level || "none" });
      document.title = "Report · CodeAtlas";
    }
  }, [results]);

  if (error) {
    const gone = status === "gone";
    return (
      <div className="mx-auto max-w-xl px-4 py-16 sm:px-6 md:py-24">
        <h1 className="text-3xl font-semibold sm:text-4xl">{gone ? "This analysis has expired" : "The analysis didn't finish"}</h1>
        <p className="mt-4 text-muted">{error}</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/#start" className="rounded-lg bg-ink px-4 py-2.5 font-medium text-paper hover:opacity-90">
            Start a new analysis
          </Link>
          {!gone && (
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="rounded-lg border border-rule px-4 py-2.5 hover:border-ink"
            >
              Check again
            </button>
          )}
          <Link href="/reports" className="rounded-lg px-4 py-2.5 text-accent underline underline-offset-4">
            Open saved reports
          </Link>
        </div>
      </div>
    );
  }

  if (!results) return <AnalysisProgress status={status} taskId={taskId} />;

  return <ResultsView result={results} />;
}