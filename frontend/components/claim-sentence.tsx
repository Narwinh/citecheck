"use client";

import { Minus, PencilLine } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { cn } from "@/lib/cn";
import type { ClaimView } from "@/lib/research";

import { CitationChip } from "./citation-chip";

const TEXT_STYLE: Record<ClaimView["state"], string> = {
  verifying: "decoration-rule-strong decoration-dashed underline decoration-1 underline-offset-[0.28em]",
  supported: "decoration-supported/70 underline decoration-[1.5px] underline-offset-[0.28em]",
  partial: "decoration-partial underline decoration-dotted decoration-2 underline-offset-[0.3em]",
  unsupported: "text-unsupported line-through decoration-unsupported/80 decoration-[1.5px]",
  rewritten: "decoration-supported/70 underline decoration-[1.5px] underline-offset-[0.28em]",
  removed: "",
};

interface Props {
  claim: ClaimView;
  active?: boolean;
  activeSource?: number | null;
  onActivate?: (claimId: number | null) => void;
  onSourceActivate?: (sourceId: number | null) => void;
  onSourceSelect?: (sourceId: number) => void;
}

/** One sentence of the answer, decorated by its verification state. */
export function ClaimSentence({
  claim,
  active,
  activeSource,
  onActivate,
  onSourceActivate,
  onSourceSelect,
}: Props) {
  const reduce = useReducedMotion();

  if (claim.state === "removed") {
    return (
      <motion.span
        layout={!reduce}
        initial={false}
        className="my-0.5 inline-flex items-center gap-1.5 rounded-sm border border-dashed border-unsupported/50 px-2 py-0.5 align-middle font-mono text-[0.72rem] text-unsupported"
        title={claim.verdict?.rationale ?? claim.text}
      >
        <Minus aria-hidden className="size-3" strokeWidth={2.5} />
        claim removed: no cited source supported it
        <span className="sr-only">. Original claim: {claim.text}</span>
      </motion.span>
    );
  }

  return (
    <motion.span
      layout={!reduce}
      tabIndex={0}
      role="button"
      aria-describedby={`claim-${claim.id}-state`}
      onMouseEnter={() => onActivate?.(claim.id)}
      onMouseLeave={() => onActivate?.(null)}
      onFocus={() => onActivate?.(claim.id)}
      className={cn(
        "rounded-[2px] outline-none transition-colors [box-decoration-break:clone]",
        active && "bg-paper-sunken",
      )}
    >
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={claim.text}
          initial={reduce ? false : { opacity: 0, filter: "blur(2px)" }}
          animate={{ opacity: 1, filter: "blur(0px)" }}
          exit={reduce ? undefined : { opacity: 0 }}
          transition={{ duration: 0.35 }}
          className={cn("transition-[text-decoration-color,color] duration-500", TEXT_STYLE[claim.state])}
        >
          {claim.text}
        </motion.span>
      </AnimatePresence>
      {claim.state === "rewritten" && (
        <span className="ml-1 inline-flex translate-y-[-0.1em] items-center gap-0.5 align-middle font-mono text-[0.62rem] tracking-wide text-supported uppercase">
          <PencilLine aria-hidden className="size-3" /> revised
        </span>
      )}
      {claim.citation_ids.map((id) => (
        <CitationChip
          key={id}
          id={id}
          state={claim.state}
          active={activeSource === id}
          onActivate={onSourceActivate}
          onSelect={onSourceSelect}
        />
      ))}
      <span id={`claim-${claim.id}-state`} className="sr-only">
        {claim.state === "verifying" ? "Being checked" : claim.state}
      </span>{" "}
    </motion.span>
  );
}
