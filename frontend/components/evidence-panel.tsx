"use client";

import { Quote } from "lucide-react";

import { cn } from "@/lib/cn";
import type { ClaimView } from "@/lib/research";
import type { PassageCard } from "@/lib/types";

import { STATE_META, VerdictTag } from "./verdict";

/** Split passage text around the evidence span, tolerating case and whitespace differences. */
export function locateSpan(text: string, span: string | null): [string, string, string] | null {
  if (!span) return null;
  const direct = text.toLowerCase().indexOf(span.toLowerCase());
  if (direct !== -1) return [text.slice(0, direct), text.slice(direct, direct + span.length), text.slice(direct + span.length)];

  // Whitespace-insensitive search: map normalized positions back to the original text.
  const positions: number[] = [];
  let normalized = "";
  for (let i = 0; i < text.length; i++) {
    const ch = /\s/.test(text[i]) ? " " : text[i].toLowerCase();
    if (ch === " " && normalized.endsWith(" ")) continue;
    normalized += ch;
    positions.push(i);
  }
  const needle = span.toLowerCase().replace(/\s+/g, " ").trim();
  const at = normalized.indexOf(needle);
  if (at === -1) return null;
  const start = positions[at];
  const end = positions[at + needle.length - 1] + 1;
  return [text.slice(0, start), text.slice(start, end), text.slice(end)];
}

/** Trim long passages to a window around the evidence. */
function windowed([before, match, after]: [string, string, string], radius = 220) {
  const head = before.length > radius ? "…" + before.slice(-radius).replace(/^\S*\s/, "") : before;
  const tail = after.length > radius ? after.slice(0, radius).replace(/\s\S*$/, "") + "…" : after;
  return [head, match, tail] as const;
}

export function EvidencePanel({
  claim,
  sources,
  className,
}: {
  claim: ClaimView | null;
  sources: PassageCard[];
  className?: string;
}) {
  if (!claim) {
    return (
      <div className={cn("rounded-md border border-dashed border-rule p-4", className)}>
        <p className="kicker">Evidence</p>
        <p className="mt-2 font-serif text-sm text-ink-muted italic">
          Hover or focus a sentence to see the exact passage the verifier matched it to.
        </p>
      </div>
    );
  }

  const verdict = claim.verdict;
  const meta = STATE_META[claim.state];
  const cited = sources.filter((s) => claim.citation_ids.includes(s.id));
  const located = cited
    .map((s) => ({ source: s, parts: locateSpan(s.text, verdict?.evidence_span ?? null) }))
    .find((x) => x.parts);
  const shown = located?.source ?? cited[0];

  return (
    <div className={cn("rounded-md border border-rule bg-paper-raised p-4 shadow-card", className)}>
      <div className="flex flex-wrap items-center gap-2">
        <p className="kicker">Evidence for claim {claim.id}</p>
        <VerdictTag state={claim.state} className="ml-auto" />
      </div>

      {verdict?.rationale && (
        <p className="mt-3 font-serif text-[0.95rem] leading-snug text-ink italic">{verdict.rationale}</p>
      )}

      {claim.original && (
        <p className="mt-3 font-serif text-sm text-ink-muted">
          <span className="kicker mr-2">Originally</span>
          <span className="line-through decoration-unsupported/70">{claim.original.text}</span>
        </p>
      )}

      {shown && (
        <figure className="mt-4 border-l-2 border-rule pl-3">
          <figcaption className="mb-1.5 flex items-center gap-1.5 font-mono text-[0.68rem] text-ink-faint">
            <Quote aria-hidden className="size-3" />[{shown.id}] {shown.domain}
          </figcaption>
          <blockquote className="font-serif text-[0.88rem] leading-relaxed text-ink-muted">
            {located?.parts ? (
              (() => {
                const [head, match, tail] = windowed(located.parts);
                return (
                  <>
                    {head}
                    <mark className={cn("rounded-[2px] px-0.5 text-ink [box-decoration-break:clone]", meta.soft)}>
                      {match}
                    </mark>
                    {tail}
                  </>
                );
              })()
            ) : (
              <>
                {shown.snippet}
                <span className="mt-2 block font-mono text-[0.68rem] text-ink-faint not-italic">
                  {claim.state === "verifying"
                    ? "Waiting for the verifier."
                    : "No sentence in the cited passage supports this claim."}
                </span>
              </>
            )}
          </blockquote>
        </figure>
      )}
    </div>
  );
}
