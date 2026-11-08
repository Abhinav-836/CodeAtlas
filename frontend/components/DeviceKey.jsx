"use client";

import { useState } from "react";
import { errorMessage, reportsAPI } from "@/lib/api";
import { getOwnerToken, isValidKey, setOwnerToken } from "@/lib/owner";
import { toast } from "@/lib/toast";
import { track } from "@/lib/track";
import Modal from "./Modal";

/**
 * CodeAtlas has no accounts: a browser's reports belong to its secret key.
 * To see the same reports on another device, copy the key there.
 */
export default function DeviceKey({ onSwitched }) {
  const [open, setOpen] = useState(false);
  const [show, setShow] = useState(false);
  const [pasted, setPasted] = useState("");
  const [moveMine, setMoveMine] = useState(true);
  const [busy, setBusy] = useState(false);
  const myKey = open ? getOwnerToken() : "";

  const copyKey = async () => {
    try {
      await navigator.clipboard.writeText(getOwnerToken());
      toast("Key copied. Paste it on your other device.", "success");
    } catch {
      setShow(true);
      toast("Couldn't copy — select the key and copy it yourself.", "error");
    }
  };

  const useKey = async (e) => {
    e.preventDefault();
    const key = pasted.trim();
    if (!isValidKey(key)) {
      toast("That key isn't valid. Copy it again from the other device.", "error");
      return;
    }
    if (key === getOwnerToken()) {
      toast("That's already this browser's key.", "error");
      return;
    }
    setBusy(true);
    try {
      let moved = 0;
      if (moveMine) moved = (await reportsAPI.transfer(key)).data.moved;
      setOwnerToken(key);
      track("device_key_used", { moved });
      toast(moved ? `Switched. ${moved} report${moved === 1 ? "" : "s"} from this browser moved across too.` : "Switched to the other device's reports.", "success");
      setOpen(false);
      setPasted("");
      onSwitched?.();
    } catch (err) {
      toast(errorMessage(err, "Couldn't switch keys."), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="text-accent underline underline-offset-4">
        Use on another device
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="Your reports on another device" wide>
        <p className="text-muted">
          There are no accounts: your reports belong to a secret key saved in this browser. Copy the key to another device and
          it sees the same reports. Treat it like a password — anyone with it can open and delete your reports.
        </p>

        <section className="mt-6">
          <h3 className="font-sans text-base font-semibold tracking-normal">On this device</h3>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-lg border border-rule bg-paper px-3 py-2 font-mono text-xs">
              {show ? myKey : "•".repeat(32)}
            </code>
            <button type="button" onClick={() => setShow((v) => !v)} className="rounded-lg px-3 py-2 text-sm text-muted hover:text-ink">
              {show ? "Hide" : "Show"}
            </button>
            <button type="button" onClick={copyKey} className="rounded-lg bg-ink px-3 py-2 text-sm text-paper hover:opacity-90">
              Copy key
            </button>
          </div>
        </section>

        <form onSubmit={useKey} className="mt-8 border-t border-rule pt-6">
          <h3 className="font-sans text-base font-semibold tracking-normal">Use a key from another device</h3>
          <label htmlFor="device-key" className="sr-only">
            Key from your other device
          </label>
          <input
            id="device-key"
            value={pasted}
            onChange={(e) => setPasted(e.target.value)}
            placeholder="Paste the key here"
            autoComplete="off"
            spellCheck={false}
            className="mt-2 w-full rounded-lg border border-rule bg-paper px-3 py-2 font-mono text-xs outline-none focus:border-accent"
          />
          <label className="mt-3 flex items-start gap-2 text-sm">
            <input type="checkbox" checked={moveMine} onChange={(e) => setMoveMine(e.target.checked)} className="mt-0.5" />
            <span>
              Also move the reports made in this browser, so nothing is left behind
            </span>
          </label>
          <div className="mt-5 flex justify-end">
            <button type="submit" disabled={busy || !pasted.trim()} className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-paper hover:opacity-90 disabled:opacity-50">
              {busy ? "Switching…" : "Switch to this key"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
