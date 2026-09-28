"use client";

import { useState } from "react";

import { AgentTimeline } from "@/components/agent-timeline";
import { CitationChip } from "@/components/citation-chip";
import { ClaimSentence } from "@/components/claim-sentence";
import { EvidencePanel } from "@/components/evidence-panel";
import { SourceCard } from "@/components/source-card";
import { SummaryBar } from "@/components/summary-bar";
import { ThemeToggle } from "@/components/theme-toggle";
import { VerdictTag } from "@/components/verdict";
import { MOCK_PASSAGES } from "@/lib/mock-stream";
import type { ClaimState, ClaimView, ResearchState } from "@/lib/research";

const STATES: ClaimState[] = ["verifying", "supported", "partial", "unsupported", "rewritten", "removed"];

const SAMPLE_CLAIMS: ClaimView[] = [
  {
    id: 1,
    text: "Honeybees communicate the location of food through the waggle dance.",
    citation_ids: [1],
    state: "supported",
    verdict: {
      claim_id: 1,
      label: "SUPPORTED",
      evidence_span:
        "A forager that finds a rich patch of flowers returns to the hive and performs the waggle dance on the vertical comb.",
      rationale: "The passage states that foragers perform the waggle dance after finding food.",
    },
  },
  {
    id: 2,
    text: "Longer waggle runs signal that the food source is farther from the hive.",
    citation_ids: [2],
    state: "verifying",
  },
  {
    id: 3,
    text: "Bees switch to a round dance for food sources closer than about 50 metres.",
    citation_ids: [3],
    state: "partial",
    verdict: {
      claim_id: 3,
      label: "PARTIAL",
      evidence_span: "When food is close to the hive, foragers perform a simpler round dance",
      rationale: "The round dance for nearby food is stated, but the 50-metre threshold is not.",
    },
  },
  {
    id: 4,
    text: "Karl von Frisch received the Nobel Prize in 1973 for decoding the dance.",
    citation_ids: [4],
    state: "unsupported",
    verdict: {
      claim_id: 4,
      label: "UNSUPPORTED",
      evidence_span: null,
      rationale: "The passage describes von Frisch's research but never mentions a Nobel Prize or 1973.",
    },
  },
  {
    id: 5,
    text: "For food close to the hive, bees perform a simpler round dance instead.",
    citation_ids: [3],
    state: "rewritten",
    original: {
      id: 5,
      text: "Bees switch to a round dance for food sources closer than about 50 metres.",
      citation_ids: [3],
    },
    verdict: {
      claim_id: 5,
      label: "SUPPORTED",
      evidence_span: "When food is close to the hive, foragers perform a simpler round dance",
      rationale: "The rewritten claim matches the passage without the unsupported distance.",
    },
  },
  { id: 6, text: "Honeybees can see ultraviolet flower markings.", citation_ids: [5], state: "removed" },
];

const RUNNING: ResearchState["agents"] = {
  planner: { status: "done", ms: 1043 },
  retriever: { status: "done", ms: 2291 },
  writer: { status: "running" },
  verifier: { status: "idle" },
  reviser: { status: "idle" },
};

const FINISHED: ResearchState["agents"] = {
  planner: { status: "done", ms: 1043 },
  retriever: { status: "done", ms: 2291 },
  writer: { status: "done", ms: 3284 },
  verifier: { status: "done", ms: 3162 },
  reviser: { status: "skipped" },
};

const SWATCHES = [
  ["paper", "bg-paper"],
  ["paper-raised", "bg-paper-raised"],
  ["paper-sunken", "bg-paper-sunken"],
  ["ink", "bg-ink"],
  ["ink-muted", "bg-ink-muted"],
  ["ink-faint", "bg-ink-faint"],
  ["rule", "bg-rule"],
  ["accent", "bg-accent"],
  ["supported", "bg-supported"],
  ["partial", "bg-partial"],
  ["unsupported", "bg-unsupported"],
  ["supported-soft", "bg-supported-soft"],
  ["partial-soft", "bg-partial-soft"],
  ["unsupported-soft", "bg-unsupported-soft"],
] as const;

function ThemePair({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {(["light", "dark"] as const).map((theme) => (
        <div
          key={theme}
          data-theme={theme}
          className="min-w-0 rounded-lg border border-rule bg-paper p-5 text-ink sm:p-6"
        >
          <p className="kicker mb-4">{theme}</p>
          {children}
        </div>
      ))}
    </div>
  );
}

function Section({ title, note, children }: { title: string; note: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4 border-t border-rule pt-8">
      <div className="max-w-2xl">
        <h2 className="font-serif text-2xl font-normal tracking-tight">{title}</h2>
        <p className="mt-1 font-serif text-ink-muted italic">{note}</p>
      </div>
      <ThemePair>{children}</ThemePair>
    </section>
  );
}

function ClaimsDemo() {
  const [active, setActive] = useState<number | null>(3);
  const [activeSource, setActiveSource] = useState<number | null>(null);
  const claim = SAMPLE_CLAIMS.find((c) => c.id === active) ?? null;
  return (
    <div className="space-y-5">
      <p className="font-serif text-[1.1rem] leading-[1.8]">
        {SAMPLE_CLAIMS.map((c) => (
          <ClaimSentence
            key={c.id}
            claim={c}
            active={active === c.id}
            activeSource={activeSource}
            onActivate={(id) => id !== null && setActive(id)}
            onSourceActivate={setActiveSource}
          />
        ))}
      </p>
      <EvidencePanel claim={claim} sources={MOCK_PASSAGES} />
    </div>
  );
}

export default function ComponentSandbox() {
  return (
    <main className="relative z-10 mx-auto max-w-[1400px] space-y-10 px-4 py-10 sm:px-8">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="kicker">CiteCheck · design system</p>
          <h1 className="mt-2 font-serif text-4xl font-light tracking-tight sm:text-5xl">Component sandbox</h1>
          <p className="mt-2 max-w-2xl font-serif text-lg text-ink-muted">
            Tokens, type, and every verification state, in both themes. The page itself follows the toggle;
            each panel below is pinned to one theme.
          </p>
        </div>
        <ThemeToggle />
      </header>

      <Section title="Typography" note="Newsreader for reading, IBM Plex Mono for metadata, Plex Sans only for small controls.">
        <div className="space-y-5">
          <p className="kicker">Display</p>
          <h3 className="font-serif text-[2.6rem] leading-[1.05] font-light tracking-[-0.02em] sm:text-5xl">
            Answers you can <em className="font-normal">check.</em>
          </h3>
          <p className="max-w-prose font-serif text-lg leading-relaxed text-ink-muted">
            Every sentence cites a source. Then a second agent reads the source and marks whether it
            really says so.
          </p>
          <p className="max-w-prose font-serif text-[1.05rem] leading-[1.75]">
            Body copy is set in Newsreader at a comfortable measure, with optical sizing so small text stays
            sturdy and headlines stay fine.
          </p>
          <p className="font-mono text-xs text-ink-muted tabular-nums">
            verifier · 3,162 ms · 6 claims · gemini-3.8-flash
          </p>
          <button
            type="button"
            className="rounded-md border border-rule-strong px-3 py-1.5 font-sans text-sm text-ink hover:bg-paper-sunken"
          >
            Plex Sans control
          </button>
        </div>
      </Section>

      <Section title="Color" note="A paper and ink base. Green, ochre and red are reserved for verification states.">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {SWATCHES.map(([name, cls]) => (
            <div key={name} className="space-y-1.5">
              <div className={`h-10 rounded-md border border-rule ${cls}`} />
              <p className="font-mono text-[0.68rem] text-ink-muted">{name}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Verdict states" note="Icon, word, and colour together, so no state depends on colour alone.">
        <div className="space-y-5">
          <div className="flex flex-wrap gap-2">
            {STATES.map((s) => (
              <VerdictTag key={s} state={s} />
            ))}
          </div>
          <p className="font-serif text-lg">
            Citation chips
            {STATES.filter((s) => s !== "removed").map((s, i) => (
              <CitationChip key={s} id={i + 1} state={s} />
            ))}
            <CitationChip id={9} active />
          </p>
        </div>
      </Section>

      <Section title="Answer sentences" note="Hover or tab through the sentences; the evidence panel follows.">
        <ClaimsDemo />
      </Section>

      <Section title="Sources" note="Cited, highlighted (its claim is hovered), and not cited.">
        <div className="grid gap-3">
          <SourceCard passage={MOCK_PASSAGES[0]} cited />
          <SourceCard passage={MOCK_PASSAGES[2]} cited highlighted />
          <SourceCard passage={MOCK_PASSAGES[3]} cited={false} />
        </div>
      </Section>

      <Section title="Pipeline" note="Mid-run and finished. Vertical on phones, horizontal from tablet width.">
        <div className="space-y-8">
          <AgentTimeline
            agents={RUNNING}
            subQueries={["honeybee waggle dance direction distance", "honeybee round dance scent"]}
          />
          <AgentTimeline agents={FINISHED} />
        </div>
      </Section>

      <Section title="Verification summary" note="The run at a glance.">
        <SummaryBar
          stats={{
            claims: 6,
            supported: 4,
            partial: 1,
            unsupported: 1,
            revised: 1,
            removed: 1,
            final_claims: 5,
            total_ms: 14212,
            tokens: 9315,
          }}
        />
      </Section>
    </main>
  );
}
