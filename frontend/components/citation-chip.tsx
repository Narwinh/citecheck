"use client";

import { cn } from "@/lib/cn";
import type { ClaimState } from "@/lib/research";

import { STATE_META } from "./verdict";

interface Props {
  id: number;
  state?: ClaimState;
  active?: boolean;
  onActivate?: (id: number | null) => void;
  onSelect?: (id: number) => void;
}

/** A keyboard-reachable [n] marker linking a sentence to source n. */
export function CitationChip({ id, state, active, onActivate, onSelect }: Props) {
  const meta = state && state !== "verifying" ? STATE_META[state] : null;
  const Icon = meta?.icon;
  return (
    <button
      type="button"
      aria-label={`Source ${id}${meta ? `, ${meta.label.toLowerCase()}` : ""}`}
      aria-pressed={active}
      onMouseEnter={() => onActivate?.(id)}
      onMouseLeave={() => onActivate?.(null)}
      onFocus={() => onActivate?.(id)}
      onBlur={() => onActivate?.(null)}
      onClick={() => onSelect?.(id)}
      className={cn(
        "relative mx-0.5 inline-flex h-[1.35em] translate-y-[-0.1em] items-center gap-0.5 rounded-[3px] border px-1",
        "align-middle font-mono text-[0.68em] leading-none tabular-nums transition-colors",
        meta ? [meta.text, meta.border] : "border-rule-strong text-ink-muted",
        active ? (meta ? meta.soft : "bg-accent-soft") : "bg-paper-raised hover:bg-paper-sunken",
      )}
    >
      {id}
      {Icon && <Icon aria-hidden className="size-[0.85em]" strokeWidth={2.5} />}
    </button>
  );
}
