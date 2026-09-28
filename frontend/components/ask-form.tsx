"use client";

import { ArrowRight, CornerDownLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { cn } from "@/lib/cn";
import { researchHref } from "@/lib/links";
import type { Mode } from "@/lib/types";

import { KeyInput } from "./key-input";

const MAX = 500;

export function AskForm() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<Mode>("strict");
  const id = useId();
  const ready = question.trim().length >= 3;

  function submit() {
    if (ready) router.push(researchHref(question, mode));
  }

  return (
    <div className="space-y-3">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label htmlFor={id} className="sr-only">
          Your question
        </label>
        <div className="rounded-lg border border-rule-strong bg-paper-raised shadow-card transition-colors focus-within:border-accent">
          <textarea
            id={id}
            value={question}
            maxLength={MAX}
            rows={2}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Ask a question the web can answer…"
            className="block w-full resize-none bg-transparent px-4 pt-4 pb-2 font-serif text-xl leading-snug text-ink outline-none placeholder:text-ink-faint sm:text-2xl"
          />
          <div className="flex flex-wrap items-center gap-3 border-t border-rule px-3 py-2.5">
            <fieldset className="flex rounded-md border border-rule p-0.5">
              <legend className="sr-only">Verification mode</legend>
              {(["strict", "lenient"] as const).map((m) => (
                <label
                  key={m}
                  className={cn(
                    "cursor-pointer rounded-[4px] px-2.5 py-1 font-mono text-[0.7rem] tracking-wide transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent",
                    mode === m ? "bg-ink text-paper" : "text-ink-muted hover:text-ink",
                  )}
                >
                  <input
                    type="radio"
                    name="mode"
                    value={m}
                    checked={mode === m}
                    onChange={() => setMode(m)}
                    className="sr-only"
                  />
                  {m}
                </label>
              ))}
            </fieldset>
            <p className="hidden font-serif text-xs text-ink-faint italic sm:block">
              {mode === "strict"
                ? "Only fully supported sentences survive."
                : "Partly supported sentences are kept, marked."}
            </p>
            <span className="ml-auto hidden items-center gap-1 font-mono text-[0.65rem] text-ink-faint sm:inline-flex">
              <CornerDownLeft aria-hidden className="size-3" /> to ask
            </span>
            <button
              type="submit"
              disabled={!ready}
              className="ml-auto inline-flex items-center gap-1.5 rounded-md bg-ink px-3.5 py-1.5 font-sans text-sm font-medium text-paper transition-opacity hover:opacity-90 disabled:opacity-40 sm:ml-0"
            >
              Research <ArrowRight aria-hidden className="size-3.5" />
            </button>
          </div>
        </div>
      </form>
      {/* Outside the ask form: KeyInput is its own form, and forms can't nest. */}
      <details className="group max-w-xl">
        <summary className="cursor-pointer font-mono text-[0.7rem] text-ink-faint hover:text-ink-muted">
          Use your own Gemini key (optional)
        </summary>
        <div className="mt-3">
          <KeyInput />
        </div>
      </details>
    </div>
  );
}
