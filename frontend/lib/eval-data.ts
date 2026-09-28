// Typed view of data/eval.json, which scripts/sync-eval.mjs copies from a
// committed eval run (eval/results/<run>/). Nothing on /eval is hard-coded.

import raw from "@/data/eval.json";

export type Variant = "off" | "remove_strict" | "remove_lenient" | "revise_strict" | "revise_lenient";

export interface VariantMetrics {
  claims: number;
  judged: number;
  unjudged: number;
  support_rate: number | null;
  partial_rate: number | null;
  unsupported_rate: number | null;
  citation_precision: number | null;
  removal_rate: number | null;
}

export interface Agreement {
  n: number;
  exact?: number;
  kappa?: number | null;
  pass_fail?: number;
}

export interface QuestionRow {
  id: string;
  category: string;
  question: string;
  status: "ok" | "error";
  writer_status?: string;
  draft_claims?: number;
  final_claims?: number;
  revised?: number;
  removed?: number;
  unsupported_before?: number;
  unsupported_after?: number;
  judged?: boolean;
  total_ms?: number | null;
  models?: string[];
}

export interface EvalData {
  run: string;
  summary: {
    questions: { total: number; completed: number; judged: number; by_category: Record<string, number> };
    variants: Record<Variant, VariantMetrics>;
    abstention: Record<
      "off" | "revise_strict",
      { unanswerable_questions: number; correct_abstentions: number | null; false_abstentions: number | null }
    >;
    latency: {
      total_p50_ms: number | null;
      total_p95_ms: number | null;
      per_agent: Record<string, { p50: number | null; p95: number | null; n: number }>;
      samples: number[];
    };
    tokens: {
      mean_tokens_per_question: number | null;
      mean_tokens_per_agent: Record<string, number>;
      model_calls: Record<string, number>;
    };
    verifier_vs_judge: Agreement;
    judge_vs_human: Agreement;
    per_question: QuestionRow[];
  };
  config: {
    run_id: string;
    written_at: string;
    git_commit: string | null;
    benchmark: string;
    models: { primary: string; fallbacks: string; judge: string; embedding: string };
    prompts: Record<string, string>;
  };
}

export const EVAL = raw as unknown as EvalData;

export const VARIANT_LABELS: Record<Variant, { name: string; note: string }> = {
  off: { name: "Verifier off", note: "the writer's draft, unchecked" },
  remove_strict: { name: "Verify, remove (strict)", note: "partial and unsupported claims dropped" },
  revise_strict: { name: "Verify + revise (strict)", note: "the default pipeline" },
  remove_lenient: { name: "Verify, remove (lenient)", note: "only unsupported claims dropped" },
  revise_lenient: { name: "Verify + revise (lenient)", note: "partial claims kept" },
};

export const pct = (x: number | null | undefined, digits = 1) =>
  x === null || x === undefined ? "n/a" : `${(x * 100).toFixed(digits)}%`;

export const secs = (ms: number | null | undefined) =>
  ms === null || ms === undefined ? "n/a" : `${(ms / 1000).toFixed(1)}s`;
