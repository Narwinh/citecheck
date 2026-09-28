"use client";

import { Check } from "lucide-react";

import { cn } from "@/lib/cn";
import type { AgentStatus, ResearchState } from "@/lib/research";
import type { AgentName } from "@/lib/types";

const STEPS: { agent: AgentName; label: string; blurb: string }[] = [
  { agent: "planner", label: "Planner", blurb: "splits the question" },
  { agent: "retriever", label: "Retriever", blurb: "searches and ranks sources" },
  { agent: "writer", label: "Writer", blurb: "drafts cited sentences" },
  { agent: "verifier", label: "Verifier", blurb: "checks each claim" },
  { agent: "reviser", label: "Reviser", blurb: "fixes or removes failures" },
];

function Node({ status }: { status: AgentStatus }) {
  return (
    <span
      aria-hidden
      className={cn(
        "relative z-10 inline-flex size-4 shrink-0 items-center justify-center rounded-full border-[1.5px] bg-paper",
        status === "idle" && "border-rule-strong",
        status === "skipped" && "border-dashed border-rule-strong",
        status === "running" && "border-accent",
        status === "done" && "border-ink bg-ink text-paper",
      )}
    >
      {status === "running" && (
        <span className="absolute inset-[-5px] animate-ping rounded-full border border-accent/60 motion-reduce:animate-none" />
      )}
      {status === "running" && <span className="size-1.5 rounded-full bg-accent" />}
      {status === "done" && <Check className="size-2.5" strokeWidth={3.5} />}
    </span>
  );
}

function timing(status: AgentStatus, ms?: number) {
  if (status === "running") return "running";
  if (status === "done" && ms !== undefined) return `${ms.toLocaleString("en-US")} ms`;
  if (status === "skipped") return "not needed";
  return "waiting";
}

/** planner -> retriever -> writer -> verifier -> reviser; horizontal on wide screens. */
export function AgentTimeline({
  agents,
  subQueries = [],
}: {
  agents: ResearchState["agents"];
  subQueries?: string[];
}) {
  return (
    <ol className="grid grid-cols-1 gap-0 md:grid-cols-5" aria-label="Research pipeline">
      {STEPS.map(({ agent, label, blurb }, i) => {
        const { status, ms } = agents[agent];
        const last = i === STEPS.length - 1;
        return (
          <li key={agent} className="relative flex gap-3 pb-5 md:block md:pb-0 md:pr-4">
            {/* connector: vertical on mobile, horizontal on desktop */}
            {!last && (
              <span
                aria-hidden
                className={cn(
                  "absolute top-4 left-[7px] h-[calc(100%-1rem)] w-px md:top-[7px] md:left-4 md:h-px md:w-[calc(100%-1rem)]",
                  status === "done" ? "bg-ink" : "bg-rule",
                )}
              />
            )}
            <Node status={status} />
            <div className="md:mt-3">
              <p
                className={cn(
                  "font-mono text-[0.7rem] tracking-[0.08em] uppercase",
                  status === "idle" || status === "skipped" ? "text-ink-faint" : "text-ink",
                )}
              >
                {label}
              </p>
              <p className="mt-0.5 font-mono text-[0.7rem] text-ink-faint tabular-nums" aria-live="polite">
                <span className="sr-only">{label} status: </span>
                {timing(status, ms)}
              </p>
              <p className="mt-1 font-serif text-[0.8rem] leading-snug text-ink-muted italic">{blurb}</p>
              {agent === "planner" && subQueries.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {subQueries.map((q) => (
                    <li
                      key={q}
                      className="border-l border-rule pl-2 font-mono text-[0.68rem] leading-snug text-ink-muted"
                    >
                      {q}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
