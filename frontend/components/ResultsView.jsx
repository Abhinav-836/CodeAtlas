"use client";

import { useState } from "react";
import Link from "next/link";
import { errorMessage, reportsAPI, sharedAPI } from "@/lib/api";
import { fileName, normalizeLevel, repoDisplayName, SEVERITIES } from "@/lib/format";
import { toast } from "@/lib/toast";
import { track } from "@/lib/track";
import Markdown from "./Markdown";
import ShareReport from "./ShareReport";
import { SeverityLabel, SeverityMark, severityText } from "./Severity";

const CONFIDENCE = {
  ast: "Exact (parsed syntax tree)",
  parser: "Exact (language parser)",
  heuristic: "Approximate (pattern-based)",
};

// First plain paragraph of the AI markdown, for the teaser above the tabs.
function teaser(md) {
  const out = [];
  for (const raw of String(md || "").split("\n")) {
    const line = raw.trim();
    const plain = line && !/^(#|\||[-*+] |\d+\.|```|>)/.test(line);
    if (plain) out.push(line);
    else if (out.length) break;
  }
  return out.join(" ").replace(/[*_`]/g, "").replace(/\[([^\]]+)\]\([^)]*\)/g, "$1");
}

/* ---------- Risk scale: the report's signature element ---------- */
function RiskScale({ score, level }) {
  const s = Math.max(0, Math.min(100, Number(score) || 0));
  const l = normalizeLevel(level);
  return (
    <div className="w-full sm:w-72">
      <div className="flex items-baseline justify-between">
        <span className="text-sm text-muted">Risk score</span>
        <SeverityLabel level={l} />
      </div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className={`font-display text-6xl font-semibold leading-none ${severityText(l)}`}>{s}</span>
        <span className="text-muted">/ 100</span>
      </div>
      {/* Scale bar in the style of a map's distance scale */}
      <div className="relative mt-4" role="img" aria-label={`Risk score ${s} out of 100`}>
        <div className="grid h-2 grid-cols-4 overflow-hidden rounded-sm border border-ink">
          <span className="bg-low/70" />
          <span className="bg-medium/70" />
          <span className="bg-high/70" />
          <span className="bg-critical/70" />
        </div>
        <span
          aria-hidden="true"
          className="absolute -top-1.5 h-5 w-0.5 -translate-x-1/2 bg-ink"
          style={{ left: `${s}%` }}
        />
        <div className="mt-1 flex justify-between text-xs tabular-nums text-muted">
          <span>0</span>
          <span>25</span>
          <span>50</span>
          <span>75</span>
          <span>100</span>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="mt-0.5 font-display text-2xl font-semibold">{value}</dd>
    </div>
  );
}

function EmptyNote({ children }) {
  return <p className="rounded-lg border border-dashed border-rule px-4 py-8 text-center text-muted">{children}</p>;
}

function Finding({ file, line, level, title, context, extra }) {
  return (
    <li className="py-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <SeverityMark level={level} />
        <span className="font-medium">{title}</span>
        <span className="font-mono text-sm text-muted" title={file}>
          {fileName(file)}
          {line ? `:${line}` : ""}
        </span>
        {extra}
      </div>
      {context && (
        <pre className="mt-2 overflow-x-auto rounded-lg bg-ink px-3.5 py-3 font-mono text-xs leading-relaxed text-paper">
          {context}
        </pre>
      )}
    </li>
  );
}

/* ---------- Tabs ---------- */
function OverviewTab({ result }) {
  const bySev = result?.security?.by_severity || {};
  const recs = result?.recommendations || [];
  return (
    <div className="space-y-12">
      <section>
        <h2 className="text-xl font-semibold">Findings by severity</h2>
        <dl className="mt-4 grid grid-cols-2 border-y border-rule sm:grid-cols-4">
          {SEVERITIES.map((lvl, i) => (
            <div key={lvl} className={`py-4 ${i > 0 ? "sm:border-l sm:border-rule sm:pl-5" : ""} ${i % 2 ? "border-l border-rule pl-5" : ""}`}>
              <dt>
                <SeverityLabel level={lvl} />
              </dt>
              <dd className="mt-1 font-display text-3xl font-semibold">{bySev[lvl] || 0}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section>
        <h2 className="text-xl font-semibold">What to fix first</h2>
        {recs.length ? (
          <ul className="mt-4 divide-y divide-rule border-y border-rule">
            {recs.map((rec, i) => (
              <li key={i} className="grid gap-1 py-5 sm:grid-cols-[8rem_1fr] sm:gap-6">
                <div className="flex flex-col gap-1">
                  <SeverityLabel level={rec.priority} />
                  {rec.category && <span className="text-sm capitalize text-muted">{rec.category}</span>}
                </div>
                <div>
                  <h3 className="font-sans text-base font-semibold tracking-normal">{rec.title}</h3>
                  {rec.description && <p className="mt-1 max-w-[70ch] text-muted">{rec.description}</p>}
                  {rec.action && (
                    <p className="mt-2 max-w-[70ch]">
                      <span className="font-medium">Do this: </span>
                      {rec.action}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyNote>No recommendations for this repository.</EmptyNote>
        )}
      </section>
    </div>
  );
}

function SecurityTab({ result }) {
  const secrets = result?.security?.secrets || [];
  const vulns = result?.security?.vulnerabilities || [];
  if (!secrets.length && !vulns.length) {
    return <EmptyNote>No hardcoded secrets or risky patterns were found.</EmptyNote>;
  }
  return (
    <div className="space-y-12">
      {secrets.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold">Possible hardcoded secrets ({secrets.length})</h2>
          <p className="mt-1 text-sm text-muted">Values are redacted. Rotate any real credential found here.</p>
          <ul className="mt-2 divide-y divide-rule">
            {secrets.map((s, i) => (
              <Finding
                key={i}
                file={s.file}
                line={s.line}
                level={s.risk_level}
                title={s.type || "Secret"}
                context={s.context}
                extra={s.commit ? <span className="text-sm text-muted">commit {s.commit}</span> : null}
              />
            ))}
          </ul>
        </section>
      )}
      {vulns.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold">Risky patterns ({vulns.length})</h2>
          <ul className="mt-2 divide-y divide-rule">
            {vulns.map((v, i) => (
              <Finding key={i} file={v.file} line={v.line} level={v.severity} title={v.pattern} context={v.context} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function ComplexityTab({ result }) {
  const cx = result?.complexity;
  const perLang = cx?.per_language || {};
  if (!cx || !Object.keys(perLang).length) {
    return <EmptyNote>No supported source files, so there&rsquo;s no complexity data.</EmptyNote>;
  }
  const files = (cx.most_complex_files || []).slice(0, 10);
  const maxScore = Math.max(1, ...files.map((f) => Number(f.complexity_score) || 0));
  const avg = typeof cx.avg_complexity_score === "number" ? cx.avg_complexity_score.toFixed(2) : cx.avg_complexity_score ?? 0;

  return (
    <div className="space-y-12">
      <section>
        <dl className="grid grid-cols-2 gap-6 sm:grid-cols-4">
          <Stat label="Functions" value={(cx.total_functions ?? 0).toLocaleString()} />
          <Stat label="Classes" value={(cx.total_classes ?? 0).toLocaleString()} />
          <Stat label="Average complexity" value={avg} />
          <Stat label="Lines measured" value={(cx.total_lines ?? 0).toLocaleString()} />
        </dl>
        <p className="mt-4 text-sm text-muted">Measurement: {CONFIDENCE[cx.confidence] || "File statistics only"}</p>
      </section>

      {files.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold">Most complex files</h2>
          <ul className="mt-4 space-y-4">
            {files.map((f, i) => (
              <li key={i}>
                <div className="flex items-baseline justify-between gap-4">
                  <span className="truncate font-mono text-sm" title={f.file}>
                    {fileName(f.file)}
                  </span>
                  <span className="shrink-0 font-display font-semibold">{f.complexity_score}</span>
                </div>
                <div className="mt-1.5 h-1.5 rounded-full bg-rule">
                  <div className="h-full rounded-full bg-medium" style={{ width: `${((Number(f.complexity_score) || 0) / maxScore) * 100}%` }} />
                </div>
                <p className="mt-1 text-sm text-muted">
                  {[f.language, `${f.functions ?? 0} functions`, `${f.classes ?? 0} classes`, `${f.lines ?? 0} lines`]
                    .filter(Boolean)
                    .join(", ")}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h2 className="text-xl font-semibold">By language</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[32rem] text-left text-sm">
            <thead className="text-muted">
              <tr className="border-b border-rule">
                <th className="py-2 pr-4 font-normal">Language</th>
                <th className="py-2 pr-4 text-right font-normal">Files</th>
                <th className="py-2 pr-4 text-right font-normal">Functions</th>
                <th className="py-2 pr-4 text-right font-normal">Classes</th>
                <th className="py-2 pr-4 text-right font-normal">Lines</th>
                <th className="py-2 text-right font-normal">Avg complexity</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {Object.entries(perLang).map(([lang, d]) => (
                <tr key={lang} className="border-b border-rule">
                  <td className="py-2.5 pr-4 font-medium">{lang}</td>
                  <td className="py-2.5 pr-4 text-right">{d.files}</td>
                  <td className="py-2.5 pr-4 text-right">{d.total_functions}</td>
                  <td className="py-2.5 pr-4 text-right">{d.total_classes}</td>
                  <td className="py-2.5 pr-4 text-right">{(d.total_lines ?? 0).toLocaleString()}</td>
                  <td className="py-2.5 text-right">{d.avg_complexity_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

const LANG_SHADES = ["bg-accent", "bg-low", "bg-medium", "bg-high", "bg-critical", "bg-none", "bg-contour"];

function LanguagesTab({ result }) {
  const langs = Object.entries(result?.languages?.detected_languages || {}).sort(
    (a, b) => (b[1].percentage || 0) - (a[1].percentage || 0),
  );
  if (!langs.length) return <EmptyNote>No recognised languages in this repository.</EmptyNote>;
  return (
    <section>
      <h2 className="text-xl font-semibold">Share of files by language</h2>
      <div className="mt-4 flex h-4 overflow-hidden rounded-sm border border-ink" role="img" aria-label="Language distribution">
        {langs.map(([lang, d], i) => (
          <span key={lang} className={LANG_SHADES[i % LANG_SHADES.length]} style={{ width: `${d.percentage}%` }} title={`${lang} ${d.percentage}%`} />
        ))}
      </div>
      <ul className="mt-6 grid gap-x-8 gap-y-3 sm:grid-cols-2">
        {langs.map(([lang, d], i) => (
          <li key={lang} className="flex items-center gap-3 border-b border-rule pb-3">
            <span aria-hidden="true" className={`h-3 w-3 rounded-sm ${LANG_SHADES[i % LANG_SHADES.length]}`} />
            <span className="flex-1 font-medium">{lang}</span>
            <span className="tabular-nums text-muted">
              {d.count} files, {d.percentage}%
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AiTab({ ai, unavailable }) {
  if (ai) return <Markdown source={ai} />;
  return (
    <EmptyNote>
      {unavailable
        ? "The AI service couldn't be reached for this run, so the report covers the static scan only."
        : "No AI summary was produced for this analysis."}
    </EmptyNote>
  );
}

/* ---------- Page ---------- */
/**
 * One report. `shareToken` means it was opened through a share link: read-only,
 * downloads go through the link, and there's nothing to share or manage.
 */
export default function ResultsView({ result, shareToken = null, shared = false }) {
  const viaLink = Boolean(shareToken);
  const [tab, setTab] = useState("overview");
  const [format, setFormat] = useState("pdf");
  const [downloading, setDownloading] = useState(false);

  const riskLevel = result?.overall_risk_level || result?.metrics?.risk || "none";
  const riskScore = result?.overall_risk_score ?? result?.metrics?.risk_score ?? 0;
  const rawAi = result?.ai_insights;
  const ai = rawAi && rawAi.summary && !rawAi.fallback && !rawAi.error ? rawAi : null;
  const findings = (result?.security?.vulnerabilities_found || 0) + (result?.security?.secrets_found || 0);
  const duration = result?.performance?.analysis_duration_seconds;

  const tabs = [
    { key: "overview", label: "Overview" },
    { key: "security", label: `Security${findings ? ` (${findings})` : ""}` },
    { key: "complexity", label: "Complexity" },
    { key: "languages", label: "Languages" },
    { key: "ai", label: "AI summary" },
  ];

  const canDownload = viaLink || Boolean(result?.report_id);
  const download = async () => {
    if (!canDownload || downloading) return;
    setDownloading(true);
    try {
      if (viaLink) await sharedAPI.download(shareToken, format);
      else await reportsAPI.download(result.report_id, format);
      track("report_downloaded", { format, from: viaLink ? "shared" : "results" });
    } catch (err) {
      toast(errorMessage(err, "The download failed."), "error");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 md:py-14">
      {viaLink && (
        <p role="note" className="mb-8 rounded-lg border border-rule bg-surface px-4 py-3 text-sm text-muted">
          Someone shared this CodeAtlas report with you. It&rsquo;s read-only; you can view it and download a copy.
        </p>
      )}
      <header className="flex flex-col gap-8 border-b border-rule pb-10 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-muted">Report for</p>
          <h1 className="mt-1 break-words text-4xl font-semibold sm:text-5xl">{repoDisplayName(result)}</h1>
          <dl className="mt-6 flex flex-wrap gap-x-10 gap-y-4">
            <Stat label="Files" value={(result?.summary?.total_files ?? 0).toLocaleString()} />
            <Stat label="Lines of code" value={(result?.metrics?.total_lines ?? 0).toLocaleString()} />
            <Stat label="Main language" value={result?.languages?.primary_language || "—"} />
            {typeof duration === "number" && <Stat label="Scan time" value={`${duration.toFixed(1)}s`} />}
          </dl>
        </div>
        <RiskScale score={riskScore} level={riskLevel} />
      </header>

      {ai && teaser(ai.summary) && (
        <section className="border-b border-rule py-8">
          <h2 className="text-sm font-medium text-muted">Summary</h2>
          <p className="mt-2 line-clamp-4 max-w-[70ch] text-lg">
            {teaser(ai.summary)}
          </p>
          <button type="button" onClick={() => setTab("ai")} className="mt-3 text-sm text-accent underline underline-offset-4">
            Read the full AI summary
          </button>
        </section>
      )}

      <div role="tablist" aria-label="Report sections" className="sticky top-0 z-10 -mx-4 mt-6 flex gap-1 overflow-x-auto border-b border-rule bg-paper px-4 sm:mx-0 sm:px-0">
        {tabs.map((t) => (
          <button
            key={t.key}
            role="tab"
            id={`tab-${t.key}`}
            aria-selected={tab === t.key}
            aria-controls={`panel-${t.key}`}
            onClick={() => setTab(t.key)}
            className={`-mb-px shrink-0 border-b-2 px-3 py-3 text-sm transition-colors ${
              tab === t.key ? "border-ink font-medium text-ink" : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="py-10">
        {tab === "overview" && <OverviewTab result={result} />}
        {tab === "security" && <SecurityTab result={result} />}
        {tab === "complexity" && <ComplexityTab result={result} />}
        {tab === "languages" && <LanguagesTab result={result} />}
        {tab === "ai" && <AiTab ai={ai} unavailable={Boolean(rawAi) && !ai} />}
      </div>

      <footer className="flex flex-col gap-4 border-t border-rule pt-8 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="export-format" className="text-sm text-muted">
            Download as
          </label>
          <select
            id="export-format"
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            className="rounded-lg border border-rule bg-surface px-3 py-2 text-sm"
          >
            <option value="pdf">PDF</option>
            <option value="html">HTML</option>
            <option value="markdown">Markdown</option>
            <option value="json">JSON</option>
          </select>
          <button
            type="button"
            onClick={download}
            disabled={!canDownload || downloading}
            className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-paper transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {downloading ? "Preparing…" : canDownload ? "Download report" : "Report not saved"}
          </button>
          {!viaLink && result?.report_id && <ShareReport reportId={result.report_id} shared={shared} />}
        </div>
        <Link href="/#start" className="text-sm text-accent underline underline-offset-4">
          {viaLink ? "Analyze your own repository" : "Analyze another repository"}
        </Link>
      </footer>
    </div>
  );
}