"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { errorMessage } from "@/lib/api";
import ResultsView from "./ResultsView";

/** Fetch one stored report and show it, with a clear message when it's gone. */
export default function ReportLoader({ load, shareToken = null, notFound }) {
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    let live = true;
    load()
      .then(({ data }) => {
        if (!live) return;
        setState({ status: "ready", report: data });
        document.title = "Report · CodeAtlas";
      })
      .catch((err) => {
        if (!live) return;
        const gone = err?.response?.status === 404;
        setState({ status: "error", message: gone ? notFound : errorMessage(err, "Couldn't load the report.") });
      });
    return () => {
      live = false;
    };
  }, [load, notFound]);

  if (state.status === "loading") {
    return (
      <p className="mx-auto max-w-6xl px-4 py-16 text-muted sm:px-6" role="status">
        Loading the report…
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <div className="mx-auto max-w-xl px-4 py-16 sm:px-6 md:py-24">
        <h1 className="text-3xl font-semibold sm:text-4xl">Report not available</h1>
        <p className="mt-4 text-muted">{state.message}</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/#start" className="rounded-lg bg-ink px-4 py-2.5 font-medium text-paper hover:opacity-90">
            Analyze a repository
          </Link>
          {!shareToken && (
            <Link href="/reports" className="rounded-lg px-4 py-2.5 text-accent underline underline-offset-4">
              Back to my reports
            </Link>
          )}
        </div>
      </div>
    );
  }
  return <ResultsView result={state.report} shareToken={shareToken} />;
}
