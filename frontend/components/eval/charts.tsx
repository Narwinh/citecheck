"use client";

import { Check, Contrast, X } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/cn";
import {
  pct,
  secs,
  VARIANT_LABELS,
  type EvalData,
  type Variant,
  type VariantMetrics,
} from "@/lib/eval-data";

const ORDER: Variant[] = ["off", "remove_strict", "revise_strict", "remove_lenient", "revise_lenient"];

const SEGMENTS = [
  { key: "support_rate", label: "Supported", icon: Check, fill: "bg-chart-supported" },
  { key: "partial_rate", label: "Partial", icon: Contrast, fill: "bg-chart-partial" },
  { key: "unsupported_rate", label: "Unsupported", icon: X, fill: "bg-chart-unsupported" },
] as const;

export function Legend() {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[0.7rem] text-ink-muted" aria-label="Legend">
      {SEGMENTS.map(({ key, label, icon: Icon, fill }) => (
        <li key={key} className="inline-flex items-center gap-1.5">
          <span aria-hidden className={cn("size-2.5 rounded-[2px]", fill)} />
          <Icon aria-hidden className="size-3" />
          {label}
        </li>
      ))}
    </ul>
  );
}

function Details({ m }: { m: VariantMetrics }) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-0.5 font-mono text-[0.7rem] text-ink-muted tabular-nums">
      <dt>claims judged</dt>
      <dd className="text-ink">{m.judged}</dd>
      <dt>supported</dt>
      <dd className="text-ink">{pct(m.support_rate)}</dd>
      <dt>partial</dt>
      <dd className="text-ink">{pct(m.partial_rate)}</dd>
      <dt>unsupported</dt>
      <dd className="text-ink">{pct(m.unsupported_rate)}</dd>
      <dt>citation precision</dt>
      <dd className="text-ink">{pct(m.citation_precision)}</dd>
      <dt>claims removed</dt>
      <dd className="text-ink">{pct(m.removal_rate)}</dd>
    </dl>
  );
}

/** One 100% bar per variant: how the judge labelled the claims each variant shows. */
export function VariantComposition({ variants }: { variants: EvalData["summary"]["variants"] }) {
  const [open, setOpen] = useState<Variant | null>(null);
  return (
    <div className="space-y-5">
      <Legend />
      <ol className="space-y-4">
        {ORDER.map((v) => {
          const m = variants[v];
          const segs = SEGMENTS.map((s) => ({ ...s, value: m[s.key] ?? 0 })).filter((s) => s.value > 0);
          const lead = v === "off" || v === "revise_strict";
          return (
            <li
              key={v}
              tabIndex={0}
              onMouseEnter={() => setOpen(v)}
              onMouseLeave={() => setOpen(null)}
              onFocus={() => setOpen(v)}
              onBlur={() => setOpen(null)}
              className="relative grid gap-2 rounded-sm sm:grid-cols-[13rem_minmax(0,1fr)_4.5rem] sm:items-center sm:gap-4"
            >
              <div>
                <p className={cn("font-serif text-[0.95rem] leading-tight", lead ? "text-ink" : "text-ink-muted")}>
                  {VARIANT_LABELS[v].name}
                </p>
                <p className="font-mono text-[0.65rem] text-ink-faint">{VARIANT_LABELS[v].note}</p>
              </div>
              <div
                className="flex h-5 w-full gap-[2px] bg-paper-raised"
                role="img"
                aria-label={`${VARIANT_LABELS[v].name}: ${pct(m.support_rate)} supported, ${pct(m.partial_rate)} partial, ${pct(m.unsupported_rate)} unsupported, ${m.judged} claims`}
              >
                {m.judged === 0 ? (
                  <span className="flex-1 rounded-r-[4px] bg-paper-sunken" />
                ) : (
                  segs.map((s, i) => (
                    <span
                      key={s.key}
                      className={cn(s.fill, i === segs.length - 1 && "rounded-r-[4px]")}
                      style={{ width: `${s.value * 100}%` }}
                    />
                  ))
                )}
              </div>
              <p className="font-mono text-[0.72rem] text-ink tabular-nums sm:text-right">
                {pct(m.unsupported_rate)}
                <span className="block text-[0.62rem] text-ink-faint">unsupported</span>
              </p>
              {open === v && (
                <div className="absolute top-full left-0 z-20 mt-1 w-64 rounded-md border border-rule bg-paper-raised p-3 shadow-card sm:left-[13rem]">
                  <Details m={m} />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/** Per-agent latency as a p50 to p95 range, on one shared seconds axis. */
export function LatencyRanges({ perAgent }: { perAgent: EvalData["summary"]["latency"]["per_agent"] }) {
  const order = ["planner", "retriever", "writer", "verifier", "reviser"].filter((a) => perAgent[a]);
  const max = Math.max(1000, ...order.map((a) => perAgent[a].p95 ?? 0));
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round((max * f) / 1000));
  return (
    <div className="space-y-3">
      <ul className="space-y-3">
        {order.map((a) => {
          const { p50, p95, n } = perAgent[a];
          const x50 = ((p50 ?? 0) / max) * 100;
          const x95 = ((p95 ?? 0) / max) * 100;
          return (
            <li key={a} className="grid grid-cols-[5.5rem_minmax(0,1fr)_7rem] items-center gap-3">
              <span className="font-mono text-[0.7rem] tracking-wide text-ink-muted uppercase">{a}</span>
              <div className="relative h-4" role="img" aria-label={`${a}: median ${secs(p50)}, p95 ${secs(p95)}, ${n} runs`}>
                <span aria-hidden className="absolute top-1/2 h-px w-full bg-rule" />
                <span
                  aria-hidden
                  className="absolute top-1/2 h-[2px] -translate-y-1/2 rounded-full bg-ink-muted"
                  style={{ left: `${x50}%`, width: `${Math.max(0, x95 - x50)}%` }}
                />
                <span
                  aria-hidden
                  className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ink ring-2 ring-paper"
                  style={{ left: `${x50}%` }}
                />
              </div>
              <span className="font-mono text-[0.7rem] text-ink-muted tabular-nums">
                {secs(p50)} <span className="text-ink-faint">/ {secs(p95)}</span>
              </span>
            </li>
          );
        })}
      </ul>
      <div className="grid grid-cols-[5.5rem_minmax(0,1fr)_7rem] gap-3" aria-hidden>
        <span />
        <div className="flex justify-between font-mono text-[0.62rem] text-ink-faint tabular-nums">
          {ticks.map((t, i) => (
            <span key={i}>{t}s</span>
          ))}
        </div>
        <span className="font-mono text-[0.62rem] text-ink-faint">median / p95</span>
      </div>
    </div>
  );
}

export function VariantTable({ variants }: { variants: EvalData["summary"]["variants"] }) {
  return (
    <details className="group">
      <summary className="cursor-pointer font-mono text-[0.72rem] text-accent">Show as a table</summary>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[36rem] text-left font-mono text-[0.72rem] tabular-nums">
          <thead className="text-ink-faint">
            <tr className="border-b border-rule">
              {["Variant", "Claims", "Supported", "Partial", "Unsupported", "Citation precision", "Removed"].map((h) => (
                <th key={h} className="py-1.5 pr-3 font-normal">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ORDER.map((v) => {
              const m = variants[v];
              return (
                <tr key={v} className="border-b border-rule/60 text-ink-muted">
                  <td className="py-1.5 pr-3 text-ink">{VARIANT_LABELS[v].name}</td>
                  <td className="pr-3">{m.judged}</td>
                  <td className="pr-3">{pct(m.support_rate)}</td>
                  <td className="pr-3">{pct(m.partial_rate)}</td>
                  <td className="pr-3">{pct(m.unsupported_rate)}</td>
                  <td className="pr-3">{pct(m.citation_precision)}</td>
                  <td className="pr-3">{pct(m.removal_rate)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
}
