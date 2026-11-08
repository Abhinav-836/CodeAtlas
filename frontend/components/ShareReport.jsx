"use client";

import { useState } from "react";
import { errorMessage, reportsAPI, shareUrl } from "@/lib/api";
import { toast } from "@/lib/toast";
import { track } from "@/lib/track";
import Modal from "./Modal";

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast("Link copied.", "success");
  } catch {
    toast("Couldn't copy. Select the link and copy it yourself.", "error");
  }
}

/**
 * Make, copy or turn off a read-only link to one report. The full link is
 * only known right after it's made (the server keeps a hash), so reopening
 * the dialog later offers a fresh link instead.
 */
export default function ShareReport({ reportId, shared: initiallyShared = false, onChange }) {
  const [open, setOpen] = useState(false);
  const [link, setLink] = useState("");
  const [shared, setShared] = useState(initiallyShared);
  const [busy, setBusy] = useState(false);

  const make = async () => {
    setBusy(true);
    try {
      const { data } = await reportsAPI.share(reportId);
      const url = shareUrl(data.share_token);
      setLink(url);
      setShared(true);
      onChange?.(true);
      track("report_shared");
      await copy(url);
    } catch (err) {
      toast(errorMessage(err, "Couldn't make a share link."), "error");
    } finally {
      setBusy(false);
    }
  };

  const stop = async () => {
    setBusy(true);
    try {
      await reportsAPI.unshare(reportId);
      setLink("");
      setShared(false);
      onChange?.(false);
      toast("Sharing turned off. The old link no longer works.", "success");
    } catch (err) {
      toast(errorMessage(err, "Couldn't turn sharing off."), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={!reportId}
        className="rounded-lg border border-rule px-4 py-2 text-sm hover:border-ink disabled:opacity-50"
      >
        {shared ? "Shared · manage link" : "Share"}
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="Share this report">
        <p className="text-muted">
          Anyone with the link can view and download this report — nothing else. They can&rsquo;t see your other reports or
          delete anything. Repository names, file paths and code snippets in findings are visible to them.
        </p>
        {link ? (
          <div className="mt-5">
            <label htmlFor="share-link" className="text-sm text-muted">
              Share link
            </label>
            <div className="mt-1 flex gap-2">
              <input
                id="share-link"
                readOnly
                value={link}
                onFocus={(e) => e.target.select()}
                className="min-w-0 flex-1 rounded-lg border border-rule bg-paper px-3 py-2 font-mono text-xs"
              />
              <button type="button" onClick={() => copy(link)} className="rounded-lg bg-ink px-3 py-2 text-sm text-paper hover:opacity-90">
                Copy
              </button>
            </div>
          </div>
        ) : shared ? (
          <p className="mt-4 rounded-lg bg-rule/30 px-3 py-2 text-sm">
            This report already has a share link. For security the full link is only shown once — make a new one if you need
            it again (the old one stops working).
          </p>
        ) : null}
        <div className="mt-6 flex flex-wrap justify-end gap-2">
          {shared && (
            <button type="button" onClick={stop} disabled={busy} className="mr-auto rounded-lg px-3 py-2 text-sm text-critical hover:bg-critical/5 disabled:opacity-50">
              Turn off sharing
            </button>
          )}
          <button type="button" onClick={make} disabled={busy} className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-paper hover:opacity-90 disabled:opacity-50">
            {busy ? "Working…" : link || shared ? "Make a new link" : "Create and copy link"}
          </button>
        </div>
      </Modal>
    </>
  );
}
