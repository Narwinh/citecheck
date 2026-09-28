"use client";

import { ArrowUpRight } from "lucide-react";

import { cn } from "@/lib/cn";
import type { PassageCard } from "@/lib/types";

interface Props {
  passage: PassageCard;
  cited?: boolean;
  highlighted?: boolean;
  onActivate?: (id: number | null) => void;
}

function Monogram({ domain }: { domain: string }) {
  return (
    <span
      aria-hidden
      className="inline-flex size-5 shrink-0 items-center justify-center rounded-[3px] border border-rule bg-paper-sunken font-mono text-[0.6rem] text-ink-muted uppercase"
    >
      {domain.replace(/^www\./, "").charAt(0)}
    </span>
  );
}

export function SourceCard({ passage, cited = true, highlighted, onActivate }: Props) {
  return (
    <article
      onMouseEnter={() => onActivate?.(passage.id)}
      onMouseLeave={() => onActivate?.(null)}
      className={cn(
        "group relative rounded-md border bg-paper-raised p-3 transition-all duration-300",
        highlighted
          ? "border-accent shadow-card"
          : "border-rule hover:border-rule-strong",
        !cited && !highlighted && "opacity-60",
      )}
    >
      <div className="flex items-center gap-2">
        <span className="font-mono text-[0.7rem] text-ink-faint tabular-nums">[{passage.id}]</span>
        {passage.favicon ? (
          // eslint-disable-next-line @next/next/no-img-element -- remote favicons of arbitrary sites
          <img src={passage.favicon} alt="" className="size-4 rounded-[2px]" loading="lazy" />
        ) : (
          <Monogram domain={passage.domain} />
        )}
        <span className="truncate font-mono text-[0.7rem] text-ink-muted">{passage.domain}</span>
        {cited && (
          <span className="ml-auto font-mono text-[0.6rem] tracking-wider text-ink-faint uppercase">
            cited
          </span>
        )}
      </div>
      <h3 className="mt-1.5 font-serif text-[0.95rem] leading-snug font-medium text-ink">
        <a
          href={passage.url}
          target="_blank"
          rel="noreferrer"
          className="text-ink no-underline after:absolute after:inset-0 hover:underline"
        >
          {passage.title || passage.domain}
          <ArrowUpRight aria-hidden className="ml-0.5 inline size-3.5 text-ink-faint" />
        </a>
      </h3>
      <p className="mt-1 line-clamp-3 font-serif text-[0.82rem] leading-relaxed text-ink-muted">
        {passage.snippet}
      </p>
    </article>
  );
}
