"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { errorMessage, reportsAPI } from "@/lib/api";
import { formatDate, humanSize, repoDisplayName } from "@/lib/format";
import { toast } from "@/lib/toast";
import { track } from "@/lib/track";
import Modal from "./Modal";
import { SeverityLabel } from "./Severity";

const FORMATS = [
  ["pdf", "PDF"],
  ["html", "HTML"],
  ["markdown", "Markdown"],
  ["json", "JSON"],
];

export default function ReportsBrowser() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [query, setQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");

  const [selected, setSelected] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [format, setFormat] = useState("pdf");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (q = "") => {
    setLoading(true);
    setLoadError("");
    try {
      const { data } = q ? await reportsAPI.search(q) : await reportsAPI.list();
      setReports(data.reports ?? []);
      setActiveQuery(q);
    } catch (err) {
      setLoadError(errorMessage(err, "Couldn't load your reports."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const openDetail = useCallback(async (id) => {
    try {
      const { data } = await reportsAPI.summary(id);
      setSelected(data);
      setDetailOpen(true);
    } catch (err) {
      toast(err?.response?.status === 404 ? "That report doesn't exist anymore." : errorMessage(err, "Couldn't open the report."), "error");
    }
  }, []);

  // Deep link: /reports?report=<id>
  const deepLink = searchParams.get("report");
  useEffect(() => {
    if (deepLink) openDetail(deepLink);
  }, [deepLink, openDetail]);

  const closeDetail = () => {
    setDetailOpen(false);
    if (deepLink) router.replace(pathname, { scroll: false });
  };

  const download = async (report) => {
    setBusy(true);
    try {
      await reportsAPI.download(report.id, format);
      track("report_downloaded", { format, from: "reports" });
    } catch (err) {
      toast(errorMessage(err, "The download failed."), "error");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      await reportsAPI.remove(selected.id);
      toast("Report deleted.", "success");
      track("report_deleted");
      setConfirmDelete(false);
      closeDetail();
      setSelected(null);
      await load(activeQuery);
    } catch (err) {
      toast(errorMessage(err, "Couldn't delete the report."), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          load(query.trim());
        }}
        className="mt-8 flex max-w-xl gap-2"
      >
        <label htmlFor="report-search" className="sr-only">
          Search reports
        </label>
        <input
          id="report-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by repository name"
          className="min-w-0 flex-1 rounded-lg border border-rule bg-surface px-3.5 py-2.5 outline-none focus:border-accent"
        />
        <button type="submit" className="rounded-lg bg-ink px-4 py-2.5 text-paper hover:opacity-90">
          Search
        </button>
        {activeQuery && (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              load();
            }}
            className="rounded-lg px-3 py-2.5 text-muted hover:text-ink"
          >
            Clear
          </button>
        )}
      </form>

      <div className="mt-8">
        {loading ? (
          <p className="text-muted" role="status">
            Loading reports…
          </p>
        ) : loadError ? (
          <div role="alert" className="rounded-lg border border-critical/30 bg-critical/5 px-4 py-3 text-critical">
            {loadError}{" "}
            <button type="button" onClick={() => load(activeQuery)} className="underline underline-offset-4">
              Try again
            </button>
          </div>
        ) : reports.length === 0 ? (
          <div className="rounded-lg border border-dashed border-rule px-6 py-12 text-center">
            <p className="font-medium">{activeQuery ? `No reports match “${activeQuery}”.` : "No reports yet."}</p>
            <p className="mt-1 text-muted">Every analysis you run from this browser is saved here.</p>
            <Link href="/#start" className="mt-5 inline-block rounded-lg bg-ink px-4 py-2.5 text-paper hover:opacity-90">
              Analyze a repository
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[40rem] text-left text-sm">
              <thead className="text-muted">
                <tr className="border-b border-ink">
                  <th className="py-2 pr-4 font-normal">Repository</th>
                  <th className="py-2 pr-4 font-normal">Risk</th>
                  <th className="py-2 pr-4 text-right font-normal">Secrets</th>
                  <th className="py-2 pr-4 text-right font-normal">Patterns</th>
                  <th className="py-2 pr-4 text-right font-normal">Files</th>
                  <th className="py-2 font-normal">Created</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {reports.map((r) => (
                  <tr key={r.id} className="border-b border-rule">
                    <td className="py-3 pr-4">
                      <button
                        type="button"
                        onClick={() => openDetail(r.id)}
                        className="text-left font-medium text-ink underline decoration-rule underline-offset-4 hover:decoration-ink"
                      >
                        {repoDisplayName(r)}
                      </button>
                    </td>
                    <td className="py-3 pr-4">
                      <SeverityLabel level={r.risk_level}>
                        {r.risk_score ?? 0}
                      </SeverityLabel>
                    </td>
                    <td className="py-3 pr-4 text-right">{r.secrets_found ?? 0}</td>
                    <td className="py-3 pr-4 text-right">{r.vulnerabilities_found ?? 0}</td>
                    <td className="py-3 pr-4 text-right">{r.files_analyzed ?? 0}</td>
                    <td className="py-3 text-muted">{formatDate(r.created)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal open={detailOpen} onClose={closeDetail} title={selected ? repoDisplayName(selected) : "Report"} wide>
        {selected && (
          <>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-4 text-sm">
              <div>
                <dt className="text-muted">Risk</dt>
                <dd className="mt-0.5">
                  <SeverityLabel level={selected.risk_level}>{`${selected.risk_score ?? 0} / 100`}</SeverityLabel>
                </dd>
              </div>
              <div>
                <dt className="text-muted">Created</dt>
                <dd className="mt-0.5">{formatDate(selected.created)}</dd>
              </div>
              <div>
                <dt className="text-muted">Files and lines</dt>
                <dd className="mt-0.5">
                  {selected.files_analyzed ?? 0} files, {(selected.total_lines ?? 0).toLocaleString()} lines
                </dd>
              </div>
              <div>
                <dt className="text-muted">Findings</dt>
                <dd className="mt-0.5">
                  {selected.secrets_found ?? 0} secrets, {selected.vulnerabilities_found ?? 0} risky patterns
                </dd>
              </div>
              {selected.primary_language && (
                <div>
                  <dt className="text-muted">Main language</dt>
                  <dd className="mt-0.5">{selected.primary_language}</dd>
                </div>
              )}
              <div>
                <dt className="text-muted">Report size</dt>
                <dd className="mt-0.5">{humanSize(selected.size_bytes)}</dd>
              </div>
            </dl>

            <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-rule pt-5">
              <label htmlFor="detail-format" className="sr-only">
                Format
              </label>
              <select
                id="detail-format"
                value={format}
                onChange={(e) => setFormat(e.target.value)}
                className="rounded-lg border border-rule bg-paper px-3 py-2 text-sm"
              >
                {FORMATS.map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => download(selected)}
                disabled={busy}
                className="rounded-lg bg-ink px-4 py-2 text-sm text-paper hover:opacity-90 disabled:opacity-50"
              >
                {busy ? "Preparing…" : "Download"}
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                className="ml-auto rounded-lg px-3 py-2 text-sm text-critical hover:bg-critical/5"
              >
                Delete report
              </button>
            </div>
          </>
        )}
      </Modal>

      <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete this report?">
        <p className="text-muted">
          {selected ? repoDisplayName(selected) : "This report"} will be removed from the server. This can&rsquo;t be undone.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button type="button" onClick={() => setConfirmDelete(false)} disabled={busy} className="rounded-lg px-4 py-2 text-sm hover:bg-rule/40">
            Keep it
          </button>
          <button
            type="button"
            onClick={remove}
            disabled={busy}
            className="rounded-lg bg-critical px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {busy ? "Deleting…" : "Delete report"}
          </button>
        </div>
      </Modal>
    </>
  );
}