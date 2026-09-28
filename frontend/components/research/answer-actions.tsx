"use client";

import { Check, Copy, Link2 } from "lucide-react";
import { useState } from "react";

import type { ClaimView } from "@/lib/research";
import type { PassageCard } from "@/lib/types";

/** Plain-text answer: sentences with [n] markers, then the numbered sources. */
export function answerAsText(question: string, claims: ClaimView[], sources: PassageCard[]) {
  const kept = claims.filter((c) => c.state !== "removed" && c.state !== "unsupported");
  const body = kept.map((c) => `${c.text} ${c.citation_ids.map((i) => `[${i}]`).join("")}`).join(" ");
  const used = new Set(kept.flatMap((c) => c.citation_ids));
  const refs = sources.filter((s) => used.has(s.id)).map((s) => `[${s.id}] ${s.title} (${s.url})`);
  return `${question}\n\n${body}\n\nSources:\n${refs.join("\n")}\n\nVerified with CiteCheck`;
}

function CopyButton({ label, getText, icon: Icon }: { label: string; getText: () => string; icon: typeof Copy }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(getText());
          setCopied(true);
          setTimeout(() => setCopied(false), 1800);
        } catch {}
      }}
      className="inline-flex items-center gap-1.5 rounded-md border border-rule px-2.5 py-1 font-mono text-[0.72rem] text-ink-muted hover:border-rule-strong hover:text-ink"
    >
      {copied ? <Check aria-hidden className="size-3.5 text-supported" /> : <Icon aria-hidden className="size-3.5" />}
      <span aria-live="polite">{copied ? "Copied" : label}</span>
    </button>
  );
}

export function AnswerActions({
  question,
  claims,
  sources,
}: {
  question: string;
  claims: ClaimView[];
  sources: PassageCard[];
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <CopyButton label="Copy answer with citations" icon={Copy} getText={() => answerAsText(question, claims, sources)} />
      <CopyButton label="Copy link" icon={Link2} getText={() => window.location.href} />
    </div>
  );
}
