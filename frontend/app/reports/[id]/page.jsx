"use client";

import { useCallback } from "react";
import { useParams } from "next/navigation";
import { reportsAPI } from "@/lib/api";
import ReportLoader from "@/components/ReportLoader";

export default function SavedReportPage() {
  const params = useParams();
  const id = decodeURIComponent(String(params?.id || ""));
  const load = useCallback(() => reportsAPI.get(id), [id]);
  return (
    <ReportLoader
      load={load}
      notFound="This report isn't in this browser's list. It may have been deleted, or it was made in another browser — use “Use on another device” on the My reports page to bring reports across."
    />
  );
}
