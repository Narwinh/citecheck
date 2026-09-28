"use client";

import { Play, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import { AgentTimeline } from "@/components/agent-timeline";
import { ClaimSentence } from "@/components/claim-sentence";
import { EvidencePanel } from "@/components/evidence-panel";
import { SourceCard } from "@/components/source-card";
import { SummaryBar } from "@/components/summary-bar";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/cn";
import { MOCK_QUESTION, mockStream } from "@/lib/mock-stream";
import { citedIds, initialResearchState, reduce } from "@/lib/research";
import type { ResearchEvent } from "@/lib/types";

type Action = { type: "reset" } | { type: "event"; event: ResearchEvent };

function reducer(state: ReturnType<typeof initialResearchState>, action: Action) {
  return action.type === "reset" ? initialResearchState() : reduce(state, action.event);
}

export default function MockStreamPage() {
  const [state, dispatch] = useReducer(reducer, undefined, initialResearchState);
  const [log, setLog] = useState<ResearchEvent[]>([]);
  const [speed, setSpeed] = useState(1);
  const [activeClaim, setActiveClaim] = useState<number | null>(null);
  const [activeSource, setActiveSource] = useState<number | null>(null);
  const abort = useRef<AbortController | null>(null);

  const play = useCallback(async () => {
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    dispatch({ type: "reset" });
    setLog([]);
    setActiveClaim(null);
    for await (const event of mockStream(speed, controller.signal)) {
      dispatch({ type: "event", event });
      setLog((l) => [...l, event]);
    }
  }, [speed]);

  useEffect(() => () => abort.current?.abort(), []);

  const claim = state.claims.find((c) => c.id === activeClaim) ?? null;
  const cited = citedIds(state.claims);
  const highlightSources = new Set(claim ? claim.citation_ids : activeSource ? [activeSource] : []);

  return (
    <main className="relative z-10 mx-auto max-w-6xl px-4 py-10 sm:px-8">
      <header className="flex flex-wrap items-center gap-3">
        <p className="kicker mr-auto">CiteCheck · mock stream</p>
        <div className="flex overflow-hidden rounded-md border border-rule font-mono text-xs" role="group" aria-label="Playback speed">
          {[1, 4].map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={speed === s}
              onClick={() => setSpeed(s)}
              className={cn("px-2.5 py-1.5", speed === s ? "bg-ink text-paper" : "text-ink-muted hover:bg-paper-sunken")}
            >
              {s}×
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={play}
          className="inline-flex items-center gap-1.5 rounded-md bg-ink px-3 py-1.5 font-sans text-sm text-paper hover:opacity-90"
        >
          {state.phase === "idle" ? <Play className="size-3.5" /> : <RotateCcw className="size-3.5" />}
          {state.phase === "idle" ? "Play" : "Replay"}
        </button>
        <ThemeToggle />
      </header>

      <h1 className="mt-8 max-w-3xl font-serif text-3xl leading-tight font-light tracking-tight sm:text-4xl">
        {MOCK_QUESTION}
      </h1>

      <div className="mt-8 border-y border-rule py-6">
        <AgentTimeline agents={state.agents} subQueries={state.subQueries} />
      </div>

      <div className="mt-8 grid gap-10 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-6">
          <p className="kicker">Answer</p>
          {state.claims.length === 0 ? (
            <div className="space-y-3" aria-hidden>
              {[92, 100, 84, 70].map((w) => (
                <div key={w} className="h-4 animate-pulse rounded bg-paper-sunken motion-reduce:animate-none" style={{ width: `${w}%` }} />
              ))}
            </div>
          ) : (
            <p className="font-serif text-[1.15rem] leading-[1.85]">
              {state.claims.map((c) => (
                <ClaimSentence
                  key={c.id}
                  claim={c}
                  active={activeClaim === c.id}
                  activeSource={activeSource}
                  onActivate={(id) => id !== null && setActiveClaim(id)}
                  onSourceActivate={setActiveSource}
                />
              ))}
            </p>
          )}
          {state.stats && <SummaryBar stats={state.stats} />}
          <EvidencePanel claim={claim} sources={state.sources} />
        </div>

        <aside className="space-y-3" aria-label="Sources">
          <p className="kicker">Sources</p>
          {state.sources.length === 0
            ? [0, 1, 2].map((i) => (
                <div key={i} className="h-24 animate-pulse rounded-md border border-rule bg-paper-raised motion-reduce:animate-none" />
              ))
            : state.sources.map((p) => (
                <SourceCard
                  key={p.id}
                  passage={p}
                  cited={state.claims.length === 0 || cited.has(p.id)}
                  highlighted={highlightSources.has(p.id)}
                  onActivate={setActiveSource}
                />
              ))}
        </aside>
      </div>

      <details className="mt-12 rounded-md border border-rule p-4">
        <summary className="kicker cursor-pointer">Event log ({log.length})</summary>
        <ol className="mt-3 max-h-80 space-y-1 overflow-auto font-mono text-[0.7rem] text-ink-muted">
          {log.map((e, i) => (
            <li key={i} className="truncate">
              <span className="text-ink">{e.event}</span> {JSON.stringify(e.data)}
            </li>
          ))}
        </ol>
      </details>
    </main>
  );
}
