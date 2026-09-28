import { Check, Contrast, Minus, PencilLine } from "lucide-react";

import type { FinalStats } from "@/lib/types";

/**
 * "6 claims · 4 supported · 1 revised · 1 removed · 14.2s" plus a proportion
 * bar. The bar describes the writer's draft: which claims passed as written,
 * which were revised, which stayed partial (lenient mode), which were removed.
 */
export function SummaryBar({ stats }: { stats: FinalStats }) {
  // final = supported + revised (+ partial claims kept as written, lenient mode only)
  const keptPartial = Math.max(0, stats.final_claims - stats.supported - stats.revised);
  const segments = [
    { key: "supported", n: stats.supported, className: "bg-supported" },
    { key: "revised", n: stats.revised, className: "bg-supported/45 bg-[repeating-linear-gradient(135deg,transparent_0_3px,var(--paper)_3px_5px)]" },
    { key: "partial", n: keptPartial, className: "bg-partial" },
    { key: "removed", n: stats.removed, className: "bg-unsupported" },
  ].filter((s) => s.n > 0);
  const total = segments.reduce((a, s) => a + s.n, 0) || 1;

  return (
    <div className="space-y-2">
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[0.75rem] text-ink-muted tabular-nums">
        <span className="text-ink">{stats.claims} claims</span>
        <span className="inline-flex items-center gap-1 text-supported">
          <Check aria-hidden className="size-3" strokeWidth={2.5} />
          {stats.supported} supported
        </span>
        {stats.revised > 0 && (
          <span className="inline-flex items-center gap-1 text-supported">
            <PencilLine aria-hidden className="size-3" />
            {stats.revised} revised
          </span>
        )}
        {keptPartial > 0 && (
          <span className="inline-flex items-center gap-1 text-partial">
            <Contrast aria-hidden className="size-3" />
            {keptPartial} partial
          </span>
        )}
        {stats.removed > 0 && (
          <span className="inline-flex items-center gap-1 text-unsupported">
            <Minus aria-hidden className="size-3" strokeWidth={2.5} />
            {stats.removed} removed
          </span>
        )}
        <span aria-hidden className="text-rule-strong">
          |
        </span>
        <span>{(stats.total_ms / 1000).toFixed(1)}s</span>
        <span>{stats.tokens.toLocaleString("en-US")} tokens</span>
      </p>
      <div aria-hidden className="flex h-1.5 w-full overflow-hidden rounded-full bg-paper-sunken">
        {segments.map((s) => (
          <span
            key={s.key}
            className={s.className}
            style={{ width: `${(s.n / total) * 100}%` }}
          />
        ))}
      </div>
    </div>
  );
}
