"use client";

import { useMemo, useState } from "react";

import { cn } from "@/lib/cn";
import { secs, type QuestionRow } from "@/lib/eval-data";

export function QuestionTable({ rows }: { rows: QuestionRow[] }) {
  const categories = useMemo(() => ["all", ...Array.from(new Set(rows.map((r) => r.category)))], [rows]);
  const [filter, setFilter] = useState("all");
  const shown = filter === "all" ? rows : rows.filter((r) => r.category === filter);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by category">
        {categories.map((c) => (
          <button
            key={c}
            type="button"
            aria-pressed={filter === c}
            onClick={() => setFilter(c)}
            className={cn(
              "rounded-full border px-3 py-1 font-mono text-[0.7rem] transition-colors",
              filter === c ? "border-ink bg-ink text-paper" : "border-rule text-ink-muted hover:border-rule-strong",
            )}
          >
            {c.replace("_", "-")}
          </button>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[46rem] text-left">
          <thead className="font-mono text-[0.66rem] tracking-wide text-ink-faint uppercase">
            <tr className="border-b border-rule">
              <th className="py-2 pr-3 font-normal">Question</th>
              <th className="py-2 pr-3 font-normal">Type</th>
              <th className="py-2 pr-3 font-normal">Claims</th>
              <th className="py-2 pr-3 font-normal">Revised / removed</th>
              <th className="py-2 pr-3 font-normal">Unsupported</th>
              <th className="py-2 pr-3 font-normal">Time</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.id} className="border-b border-rule/60 align-top">
                <td className="max-w-md py-2.5 pr-3">
                  <span className="mr-2 font-mono text-[0.66rem] text-ink-faint">{r.id}</span>
                  <span className="font-serif text-[0.92rem] text-ink">{r.question}</span>
                  {r.models && r.models.length > 0 && (
                    <span className="mt-0.5 block font-mono text-[0.62rem] text-ink-faint">{r.models.join(", ")}</span>
                  )}
                </td>
                <td className="py-2.5 pr-3 font-mono text-[0.7rem] text-ink-muted">{r.category.replace("_", "-")}</td>
                {r.status === "error" ? (
                  <td colSpan={4} className="py-2.5 pr-3 font-mono text-[0.7rem] text-ink-faint">
                    not completed
                  </td>
                ) : (
                  <>
                    <td className="py-2.5 pr-3 font-mono text-[0.72rem] text-ink tabular-nums">
                      {r.writer_status === "unanswerable" && r.draft_claims === 0
                        ? "abstained"
                        : `${r.draft_claims} → ${r.final_claims}`}
                    </td>
                    <td className="py-2.5 pr-3 font-mono text-[0.72rem] text-ink-muted tabular-nums">
                      {r.revised} / {r.removed}
                    </td>
                    <td className="py-2.5 pr-3 font-mono text-[0.72rem] text-ink-muted tabular-nums">
                      {r.judged ? `${r.unsupported_before} → ${r.unsupported_after}` : "not judged"}
                    </td>
                    <td className="py-2.5 pr-3 font-mono text-[0.72rem] text-ink-muted tabular-nums">
                      {secs(r.total_ms)}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
