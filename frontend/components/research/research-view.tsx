"use client";

import { SearchX } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { AgentTimeline } from "@/components/agent-timeline";
import { ClaimSentence } from "@/components/claim-sentence";
import { EvidencePanel } from "@/components/evidence-panel";
import { SourceCard } from "@/components/source-card";
import { SummaryBar } from "@/components/summary-bar";
import { cn } from "@/lib/cn";
import { citedIds } from "@/lib/research";
import type { Mode } from "@/lib/types";
import { useResearch } from "@/lib/use-research";

import { AnswerActions } from "./answer-actions";
import {
  FailedPanel,
  PipelineErrorPanel,
  RateLimitedPanel,
  WarmingPanel,
} from "./status-panels";

function AnswerSkeleton() {
  return (
    <div className="space-y-3" aria-hidden>
      {[96, 100, 88, 94, 62].map((w, i) => (
        <div
          key={i}
          className="h-[1.1rem] animate-pulse rounded-sm bg-paper-sunken motion-reduce:animate-none"
          style={{ width: `${w}%`, animationDelay: `${i * 120}ms` }}
        />
      ))}
    </div>
  );
}

function NoAnswer({ title, missing }: { title: string; missing: string | null }) {
  return (
    <div className="rounded-md border border-rule bg-paper-raised p-5">
      <div className="flex items-start gap-3">
        <SearchX aria-hidden className="mt-1 size-5 shrink-0 text-ink-muted" />
        <div className="space-y-2">
          <h2 className="font-serif text-xl leading-snug">{title}</h2>
          {missing && <p className="font-serif text-ink-muted">{missing}</p>}
          <p className="font-serif text-sm text-ink-faint italic">
            CiteCheck would rather say so than guess. Try rephrasing, or ask something the web has
            sources for.
          </p>
        </div>
      </div>
    </div>
  );
}

export function ResearchView({ question, mode, demo }: { question: string; mode: Mode; demo: boolean }) {
  const { state, connection, retry } = useResearch({ question, mode, demo });
  const [activeClaim, setActiveClaim] = useState<number | null>(null);
  const [lastClaim, setLastClaim] = useState<number | null>(null);
  const [activeSource, setActiveSource] = useState<number | null>(null);

  const hoverClaim = (id: number | null) => {
    setActiveClaim(id);
    if (id !== null) setLastClaim(id);
  };
  const selectSource = (id: number) => {
    document.getElementById(`source-${id}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    setActiveSource(id);
  };

  const evidenceClaim = state.claims.find((c) => c.id === (activeClaim ?? lastClaim)) ?? null;
  const cited = citedIds(state.claims);
  const focusClaim = state.claims.find((c) => c.id === activeClaim);
  const litSources = new Set(focusClaim ? focusClaim.citation_ids : activeSource ? [activeSource] : []);
  const done = state.phase === "done";
  const visible = state.claims.filter((c) => c.state !== "removed");
  const demoHref = "/research?demo=1";

  let status: React.ReactNode = null;
  if (connection.kind === "warming") status = <WarmingPanel since={connection.since} demoHref={demoHref} />;
  else if (connection.kind === "rate_limited")
    status = <RateLimitedPanel retryAt={connection.retryAt} message={connection.message} onRetry={retry} />;
  else if (connection.kind === "failed") status = <FailedPanel message={connection.message} onRetry={retry} />;
  else if (state.error) status = <PipelineErrorPanel {...state.error} onRetry={retry} />;

  const waitingForAnswer = !status && state.claims.length === 0 && !done;

  return (
    <main className="relative z-10 mx-auto max-w-6xl px-4 pt-10 pb-24 sm:px-8">
      <div className="flex flex-wrap items-center gap-2">
        <p className="kicker">Question</p>
        <span className="rounded-sm border border-rule px-1.5 py-0.5 font-mono text-[0.62rem] tracking-wider text-ink-muted uppercase">
          {mode} mode
        </span>
        {demo && (
          <span className="rounded-sm border border-accent/50 bg-accent-soft px-1.5 py-0.5 font-mono text-[0.62rem] tracking-wider text-accent uppercase">
            recorded demo
          </span>
        )}
        <Link href="/" className="ml-auto font-mono text-xs">
          Ask another
        </Link>
      </div>
      <h1 className="mt-3 max-w-4xl font-serif text-[2rem] leading-[1.12] font-light tracking-[-0.015em] sm:text-[2.6rem]">
        {question}
      </h1>

      <section aria-label="Pipeline progress" className="mt-8 border-y border-rule py-6">
        <AgentTimeline agents={state.agents} subQueries={state.subQueries} />
      </section>

      {status && <div className="mt-8 max-w-3xl">{status}</div>}

      <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_330px] lg:gap-14">
        <section aria-label="Answer" className="min-w-0 space-y-6">
          <div className="flex items-baseline justify-between gap-4">
            <p className="kicker">Answer</p>
            {state.phase === "running" && state.claims.length > 0 && !done && (
              <p className="font-mono text-[0.68rem] text-ink-faint" aria-live="polite">
                checking each sentence against its source…
              </p>
            )}
          </div>

          {waitingForAnswer && <AnswerSkeleton />}

          {done && state.claims.length === 0 && (
            <NoAnswer title="The sources don't answer this question." missing={state.missing} />
          )}
          {done && state.claims.length > 0 && visible.length === 0 && (
            <NoAnswer title="Nothing in the draft survived verification." missing={state.missing} />
          )}

          {state.claims.length > 0 && (
            <p className="font-serif text-[1.18rem] leading-[1.85] text-ink">
              {state.claims.map((c, i) => (
                <ClaimSentence
                  key={c.id}
                  claim={c}
                  index={i}
                  active={
                    activeClaim === c.id || (activeSource !== null && c.citation_ids.includes(activeSource))
                  }
                  activeSource={activeSource}
                  onActivate={hoverClaim}
                  onSourceActivate={setActiveSource}
                  onSourceSelect={selectSource}
                />
              ))}
            </p>
          )}

          {done && state.missing && visible.length > 0 && (
            <p className="border-l-2 border-partial/60 pl-3 font-serif text-sm text-ink-muted italic">
              Not covered by the sources: {state.missing}
            </p>
          )}

          {state.stats && (
            <div className="space-y-4 border-t border-rule pt-5">
              <SummaryBar stats={state.stats} />
              <AnswerActions question={question} claims={state.claims} sources={state.sources} />
            </div>
          )}

          {state.claims.length > 0 && <EvidencePanel claim={evidenceClaim} sources={state.sources} />}
        </section>

        <aside aria-label="Sources" className="space-y-3 lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)] lg:self-start lg:overflow-y-auto lg:pr-1">
          <div className="flex items-baseline justify-between">
            <p className="kicker">Sources</p>
            {state.sources.length > 0 && (
              <p className="font-mono text-[0.68rem] text-ink-faint">
                {state.claims.length ? `${cited.size} of ${state.sources.length} cited` : `${state.sources.length} found`}
              </p>
            )}
          </div>
          {state.sources.length === 0
            ? !status &&
              [0, 1, 2].map((i) => (
                <div
                  key={i}
                  aria-hidden
                  className="h-28 animate-pulse rounded-md border border-rule bg-paper-raised motion-reduce:animate-none"
                />
              ))
            : state.sources.map((p) => (
                <div key={p.id} id={`source-${p.id}`} className={cn("scroll-mt-6")}>
                  <SourceCard
                    passage={p}
                    cited={state.claims.length === 0 || cited.has(p.id)}
                    highlighted={litSources.has(p.id)}
                    onActivate={setActiveSource}
                  />
                </div>
              ))}
        </aside>
      </div>
    </main>
  );
}
