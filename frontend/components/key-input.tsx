"use client";

import { KeyRound } from "lucide-react";
import { useId, useState } from "react";

import { setApiKey, useApiKey } from "@/lib/key-store";

/** Optional: the visitor's own Gemini key, held in memory for this tab only. */
export function KeyInput({ onSaved }: { onSaved?: () => void }) {
  const current = useApiKey();
  const [value, setValue] = useState("");
  const id = useId();

  if (current) {
    return (
      <p className="flex flex-wrap items-center gap-2 font-mono text-xs text-ink-muted">
        <KeyRound aria-hidden className="size-3.5" />
        Using your key for this tab.
        <button
          type="button"
          onClick={() => setApiKey("")}
          className="text-accent underline underline-offset-2"
        >
          Forget it
        </button>
      </p>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!value.trim()) return;
        setApiKey(value);
        setValue("");
        onSaved?.();
      }}
      className="space-y-2"
    >
      <label htmlFor={id} className="kicker block">
        Your Gemini API key (optional)
      </label>
      <div className="flex gap-2">
        <input
          id={id}
          type="password"
          autoComplete="off"
          spellCheck={false}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="AIza…"
          className="min-w-0 flex-1 rounded-md border border-rule-strong bg-paper-raised px-3 py-1.5 font-mono text-sm text-ink placeholder:text-ink-faint"
        />
        <button
          type="submit"
          className="rounded-md bg-ink px-3 py-1.5 font-sans text-sm text-paper hover:opacity-90"
        >
          Use key
        </button>
      </div>
      <p className="font-serif text-xs text-ink-faint italic">
        Kept in memory for this tab only and sent straight to the research engine. Never stored or logged.
      </p>
    </form>
  );
}
