import { Suspense } from "react";
import ReportsBrowser from "@/components/ReportsBrowser";

export const metadata = { title: "My reports" };

export default function ReportsPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 md:py-14">
      <h1 className="text-4xl font-semibold">My reports</h1>
      <p className="mt-3 max-w-[60ch] text-muted">
        Reports are tied to this browser. Clearing site data or switching browsers starts an empty list.
      </p>
      <Suspense fallback={<p className="mt-10 text-muted">Loading reports…</p>}>
        <ReportsBrowser />
      </Suspense>
    </div>
  );
}