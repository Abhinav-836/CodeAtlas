"use client";

import Link from "next/link";
import { STAGES, stageIndex } from "@/lib/useAnalysis";

export default function AnalysisProgress({ status, taskId }) {
  const current = stageIndex(status);
  return (
    <div className="mx-auto max-w-xl px-4 py-16 sm:px-6 md:py-24">
      <h1 className="text-3xl font-semibold sm:text-4xl">Surveying the repository</h1>
      <p className="mt-3 text-muted">
        This page updates on its own. If the server was asleep, the first step can sit for up to a minute.
      </p>

      <ol className="mt-10 border-l border-rule" aria-label="Analysis progress">
        {STAGES.map((stage, i) => {
          const done = i < current;
          const active = i === current;
          return (
            <li key={stage.key} className="relative pb-6 pl-7 last:pb-0" aria-current={active ? "step" : undefined}>
              <span
                aria-hidden="true"
                className={`absolute -left-[7px] top-1.5 h-3.5 w-3.5 rounded-full border-2 ${
                  done ? "border-low bg-low" : active ? "border-accent bg-paper" : "border-rule bg-paper"
                }`}
              >
                {active && <span className="absolute inset-0 animate-ping rounded-full bg-accent/40" />}
              </span>
              <span className={done ? "text-muted" : active ? "font-medium" : "text-muted/70"}>{stage.label}</span>
              <span className="sr-only">{done ? " (done)" : active ? " (in progress)" : ""}</span>
            </li>
          );
        })}
      </ol>

      <p className="mt-10 text-sm text-muted">
        Analysis <span className="font-mono break-all">{taskId}</span>
      </p>
      <Link href="/#start" className="mt-2 inline-block text-sm text-accent underline underline-offset-4">
        Start a different analysis
      </Link>
    </div>
  );
}