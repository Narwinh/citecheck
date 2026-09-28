import { TriangleAlert } from "lucide-react";
import type { Metadata } from "next";

import { LatencyRanges, VariantComposition, VariantTable } from "@/components/eval/charts";
import { QuestionTable } from "@/components/eval/question-table";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { EVAL, pct, secs } from "@/lib/eval-data";

export const metadata: Metadata = {
  title: "Evaluation",
  description: "How much does verification reduce unsupported claims? Measured on a benchmark.",
};

const TARGET_QUESTIONS = 30;

function StatTile({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded-md border border-rule bg-paper-raised p-4">
      <p className="font-sans text-[0.8rem] text-ink-muted">{label}</p>
      <p className="mt-1 font-sans text-[1.9rem] leading-tight font-semibold tracking-tight text-ink">{value}</p>
      {detail && <p className="mt-1 font-mono text-[0.66rem] text-ink-faint">{detail}</p>}
    </div>
  );
}

function Section({ kicker, title, children }: { kicker: string; title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-5 border-t border-rule pt-8">
      <div>
        <p className="kicker">{kicker}</p>
        <h2 className="mt-1 font-serif text-2xl font-normal tracking-tight">{title}</h2>
      </div>
      {children}
    </section>
  );
}

export default function EvalPage() {
  const { summary: s, config, run } = EVAL;
  const off = s.variants.off;
  const full = s.variants.revise_strict;
  const preliminary = s.questions.completed < TARGET_QUESTIONS;
  const vj = s.verifier_vs_judge;
  const jh = s.judge_vs_human;

  return (
    <>
      <SiteHeader />
      <main className="relative z-10 mx-auto max-w-6xl space-y-10 px-4 pt-10 pb-20 sm:px-8">
        <header className="max-w-3xl space-y-4">
          <p className="kicker">Evaluation · run {run}</p>
          <h1 className="font-serif text-[2.3rem] leading-[1.08] font-light tracking-[-0.015em] sm:text-5xl">
            Does checking citations make answers more trustworthy?
          </h1>
          <p className="font-serif text-lg leading-relaxed text-ink-muted">
            Each benchmark question runs through the pipeline once. An independent judge (a different
            model and prompt from the verifier) then labels every claim against its cited passages, both
            before and after verification.
          </p>
        </header>

        {preliminary && (
          <div role="note" className="flex max-w-3xl gap-3 rounded-md border border-partial/50 bg-partial-soft/40 p-4">
            <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-partial" />
            <p className="font-serif text-[0.95rem] text-ink">
              Preliminary: {s.questions.completed} of {TARGET_QUESTIONS} development questions have run so far.
              These numbers are real but too few to draw conclusions from, and will change as the benchmark
              completes.
            </p>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Unsupported claims, verifier off"
            value={pct(off.unsupported_rate)}
            detail={`${off.judged} claims judged`}
          />
          <StatTile
            label="Unsupported claims, full pipeline"
            value={pct(full.unsupported_rate)}
            detail={`${full.judged} claims judged · ${pct(full.removal_rate)} removed`}
          />
          <StatTile
            label="Citation precision, full pipeline"
            value={pct(full.citation_precision)}
            detail="citations whose passage supports the claim"
          />
          <StatTile
            label="Median time per question"
            value={secs(s.latency.total_p50_ms)}
            detail={`p95 ${secs(s.latency.total_p95_ms)} · ${s.tokens.mean_tokens_per_question ?? "n/a"} tokens`}
          />
        </div>

        <Section kicker="Before and after" title="How the judge labelled each variant's claims">
          <p className="max-w-3xl font-serif text-ink-muted">
            &ldquo;Verifier off&rdquo; is the writer&rsquo;s draft. The other rows are computed from the same
            run: removing rejected claims, or revising them once and re-checking. Lenient mode keeps claims
            the verifier marked partial. Hover or focus a row for details.
          </p>
          <VariantComposition variants={s.variants} />
          <VariantTable variants={s.variants} />
        </Section>

        <div className="grid gap-10 lg:grid-cols-2">
          <Section kicker="Latency" title="Where the time goes">
            <LatencyRanges perAgent={s.latency.per_agent} />
          </Section>
          <Section kicker="Agreement" title="Can the judge be trusted?">
            <div className="grid gap-3 sm:grid-cols-2">
              <StatTile
                label="Verifier vs judge"
                value={vj.n ? pct(vj.exact ?? null, 0) : "n/a"}
                detail={vj.n ? `exact labels, n=${vj.n} · kappa ${vj.kappa ?? "n/a"}` : "no judged claims yet"}
              />
              <StatTile
                label="Judge vs human labels"
                value={jh.n ? pct(jh.exact ?? null, 0) : "pending"}
                detail={jh.n ? `n=${jh.n} · kappa ${jh.kappa ?? "n/a"}` : "hand-labelled sample comes next"}
              />
            </div>
            <p className="font-serif text-sm text-ink-muted">
              An LLM judge is only useful if it agrees with people. A sample of claims is labelled by hand
              and compared with the judge; kappa corrects agreement for chance.
            </p>
          </Section>
        </div>

        <Section kicker="Benchmark" title="Every question">
          <QuestionTable rows={s.per_question} />
        </Section>

        <Section kicker="Method" title="How to read these numbers">
          <div className="grid max-w-4xl gap-6 font-serif text-[0.98rem] leading-relaxed text-ink-muted md:grid-cols-2">
            <p>
              <strong className="font-medium text-ink">One run, several variants.</strong> Every question runs
              once in strict mode. The draft is the &ldquo;verifier off&rdquo; answer; the removal and lenient
              variants are derived from the same verdicts and rewrite attempts, so all variants see identical
              sources and the comparison isolates the verifier.
            </p>
            <p>
              <strong className="font-medium text-ink">An independent judge.</strong> Claims are judged by{" "}
              <code className="font-mono text-[0.85em]">{config.models.judge}</code> with a separate prompt
              that labels each citation individually, which gives citation precision.
            </p>
            <p>
              <strong className="font-medium text-ink">Limitations.</strong> Development ran on free-tier
              quotas, so questions were answered by a chain of models ({config.models.primary},{" "}
              {config.models.fallbacks}); the table lists which. The lenient revise variant is derived from a
              strict run, and the judge is itself an LLM until human agreement is measured.
            </p>
            <p>
              <strong className="font-medium text-ink">Provenance.</strong> Benchmark{" "}
              <code className="font-mono text-[0.85em]">{config.benchmark}</code>, results written{" "}
              {config.written_at.slice(0, 10)}
              {config.git_commit ? ` at commit ${config.git_commit}` : ""}. Raw results are in the
              repository under <code className="font-mono text-[0.85em]">eval/results/{run}</code>.
            </p>
          </div>
        </Section>
      </main>
      <SiteFooter />
    </>
  );
}
