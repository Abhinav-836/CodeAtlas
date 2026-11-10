"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { analyzeAPI, errorMessage, uploadAPI } from "@/lib/api";
import { isValidGitHubUrl, isValidZipFile, isWithinSize, MAX_FILE_SIZE_MB } from "@/lib/validators";
import { humanSize } from "@/lib/format";
import { toast } from "@/lib/toast";
import { track } from "@/lib/track";

const SOURCES = [
  { key: "github", label: "GitHub repo" },
  { key: "zip", label: "ZIP file" },
];

export default function UploadPanel() {
  const router = useRouter();
  const [source, setSource] = useState("github");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState("idle"); // idle | uploading | cloning | starting
  const [uploadPct, setUploadPct] = useState(0);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const busy = phase !== "idle";

  const pickFile = (f) => {
    setError("");
    if (!f) return;
    if (!isValidZipFile(f)) return setError("That isn't a .zip file. Compress the project folder and try again.");
    if (!isWithinSize(f)) return setError(`That file is ${humanSize(f.size)}. The limit is ${MAX_FILE_SIZE_MB} MB.`);
    setFile(f);
  };

  const clearFile = () => {
    setFile(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setError("");

    if (source === "github") {
      if (!url.trim()) return setError("Paste a repository link first.");
      if (!isValidGitHubUrl(url)) return setError("Use a link like github.com/owner/repo, or just owner/repo.");
    } else if (!file) {
      return setError("Choose a .zip file first.");
    }

    try {
      let path;
      if (source === "github") {
        setPhase("cloning");
        const { data } = await uploadAPI.uploadGithub(url.trim());
        path = data.local_path;
      } else {
        setPhase("uploading");
        setUploadPct(0);
        const { data } = await uploadAPI.uploadZip(file, setUploadPct);
        path = data.extracted_to;
      }
      setPhase("starting");
      const { data } = await analyzeAPI.start(path);
      track("analysis_started", { source });
      router.push(`/results/${encodeURIComponent(data.task_id)}`);
    } catch (err) {
      const msg = errorMessage(err, "Something went wrong starting the analysis.");
      setError(msg);
      toast(msg, "error");
      track("analysis_start_failed", { source });
      setPhase("idle");
    }
  };

  const buttonLabel = {
    idle: "Analyze repository",
    uploading: `Uploading… ${uploadPct}%`,
    cloning: "Cloning repository…",
    starting: "Starting analysis…",
  }[phase];

  return (
    <form
      onSubmit={submit}
      className="rounded-2xl border border-rule bg-surface p-5 shadow-[0_1px_0_var(--rule),0_24px_48px_-24px_rgba(23,36,43,0.25)] sm:p-6"
      aria-describedby={error ? "upload-error" : undefined}
    >
      <div role="tablist" aria-label="Where is the code?" className="mb-5 inline-flex rounded-lg border border-rule p-1 text-sm">
        {SOURCES.map((s) => (
          <button
            key={s.key}
            type="button"
            role="tab"
            aria-selected={source === s.key}
            disabled={busy}
            onClick={() => {
              setSource(s.key);
              setError("");
            }}
            className={`rounded-md px-3.5 py-1.5 transition-colors ${
              source === s.key ? "bg-ink text-paper" : "text-muted hover:text-ink"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {source === "github" ? (
        <div>
          <label htmlFor="repo-url" className="mb-2 block text-sm font-medium">
            Public repository link
          </label>
          <input
            id="repo-url"
            type="text"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            value={url}
            disabled={busy}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="github.com/vercel/next.js"
            className="w-full rounded-lg border border-rule bg-paper px-3.5 py-3 font-mono text-sm outline-none transition-colors placeholder:text-muted/70 focus:border-accent"
          />
          <p className="mt-2 text-sm text-muted">The default branch is detected for you. Private repos aren't supported.</p>
        </div>
      ) : (
        <div>
          <span className="mb-2 block text-sm font-medium">Project archive</span>
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              pickFile(e.dataTransfer.files?.[0]);
            }}
            className={`flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-4 py-6 text-center transition-colors ${
              dragging ? "border-accent bg-accent/5" : "border-rule bg-paper hover:border-muted"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".zip,application/zip"
              className="sr-only"
              disabled={busy}
              onChange={(e) => pickFile(e.target.files?.[0])}
            />
            {file ? (
              <>
                <span className="font-mono text-sm break-all">{file.name}</span>
                <span className="mt-1 text-sm text-muted">{humanSize(file.size)}</span>
              </>
            ) : (
              <>
                <span className="text-sm">
                  <span className="font-medium text-accent">Choose a .zip</span> or drop it here
                </span>
                <span className="mt-1 text-sm text-muted">Up to {MAX_FILE_SIZE_MB} MB</span>
              </>
            )}
          </label>
          {file && !busy && (
            <button type="button" onClick={clearFile} className="mt-2 text-sm text-muted underline underline-offset-4 hover:text-ink">
              Remove file
            </button>
          )}
        </div>
      )}

      {error && (
        <p id="upload-error" role="alert" className="mt-4 rounded-lg border border-critical/30 bg-critical/5 px-3.5 py-2.5 text-sm text-critical">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={busy}
        className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 font-medium text-accent-ink transition-opacity hover:opacity-90 disabled:cursor-progress disabled:opacity-70"
      >
        {busy && <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden="true" />}
        {buttonLabel}
      </button>
      <p className="mt-3 text-center text-xs text-muted">
        Only analyze code you&rsquo;re allowed to share. By continuing you agree to the{" "}
        <Link href="/terms" className="underline underline-offset-2 hover:text-ink">Terms</Link> and{" "}
        <Link href="/privacy" className="underline underline-offset-2 hover:text-ink">Privacy policy</Link>.
      </p>
      {phase === "cloning" && (
        <p className="mt-3 text-center text-sm text-muted">Large repos can take a minute to clone.</p>
      )}
    </form>
  );
}