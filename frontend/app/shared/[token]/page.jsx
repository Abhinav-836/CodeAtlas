"use client";

import { useCallback } from "react";
import { useParams } from "next/navigation";
import { sharedAPI } from "@/lib/api";
import ReportLoader from "@/components/ReportLoader";

export default function SharedReportPage() {
  const params = useParams();
  const token = decodeURIComponent(String(params?.token || ""));
  const load = useCallback(() => sharedAPI.get(token), [token]);
  return (
    <ReportLoader
      load={load}
      shareToken={token}
      notFound="This share link doesn't work. Its owner may have turned sharing off or made a new link — ask them for the current one."
    />
  );
}
