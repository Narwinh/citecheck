import type { Metadata } from "next";

import { ArchitectureDiagram } from "@/components/architecture-diagram";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: "How it works",
  description: "The four agents behind CiteCheck, and the design decisions that shaped them.",
};

const DECISIONS = [
  {
    title: "The verifier reads only the cited passage",
    body: "It never sees the rest of the sources or relies on its own knowledge. A sentence that is true but not stated in its citation fails, because the citation is what the reader will check.",
  },
  {
    title: "Evidence quotes are checked in code",
    body: "The verifier must quote the passage it relied on. If that quote can't be found in the cited text, a 'supported' verdict is downgraded to 'partial'. A verdict that can't show its work doesn't count as full support.",
  },
  {
    title: "Strict mode by default",
    body: "Partially supported sentences are sent back for revision rather than shown. Lenient mode keeps them, clearly marked. Strict is the safer default for an answer people may quote.",
  },
  {
    title: "One revision pass, not a loop",
    body: "Each extra pass costs two more model calls on the slowest part of the pipeline. A claim that fails twice is removed and flagged instead of being rewritten until something passes.",
  },
  {
    title: "Sub-queries take turns during retrieval",
    body: "Ranking all passages by one score lets an easy sub-query fill every slot, starving the second hop of a multi-hop question. Taking turns keeps evidence for every part of the question.",
  },
  {
    title: "In-memory vector store, per request",
    body: "Sources are fetched fresh for each question, so there is nothing to persist. A per-request Chroma collection needs no database server and keeps concurrent requests apart.",
  },
  {
    title: "Server-Sent Events for streaming",
    body: "Research takes 15-40 seconds. Streaming each agent's progress makes the wait legible. SSE is one-way, works over plain HTTP, and passes proxies with a heartbeat.",
  },
  {
    title: "Measured, not claimed",
    body: "An independent judge (different model and prompt) labels every claim before and after verification, and a hand-labelled sample checks the judge. The evaluation page reads committed results only.",
  },
];

export default function AboutPage() {
  return (
    <>
      <SiteHeader />
      <main className="relative z-10 mx-auto max-w-6xl space-y-14 px-4 pt-10 pb-20 sm:px-8">
        <header className="max-w-3xl space-y-4">
          <p className="kicker">How it works</p>
          <h1 className="font-serif text-[2.3rem] leading-[1.08] font-light tracking-[-0.015em] sm:text-5xl">
            Citations look trustworthy. Nothing usually checks them.
          </h1>
          <p className="font-serif text-lg leading-relaxed text-ink-muted">
            Answer engines cite sources, but a citation only says where a sentence came from, not whether the
            source supports it. CiteCheck adds an agent whose only job is to read each cited passage and
            decide whether the sentence is actually backed up, and it measures how much that helps.
          </p>
        </header>

        <section aria-labelledby="architecture" className="space-y-5">
          <h2 id="architecture" className="kicker">
            Architecture
          </h2>
          <ArchitectureDiagram />
        </section>

        <section aria-labelledby="decisions" className="space-y-6 border-t border-rule pt-8">
          <h2 id="decisions" className="font-serif text-2xl font-normal tracking-tight">
            Design decisions
          </h2>
          <ol className="grid gap-x-10 gap-y-7 md:grid-cols-2">
            {DECISIONS.map((d, i) => (
              <li key={d.title} className="grid grid-cols-[2rem_minmax(0,1fr)]">
                <span className="font-mono text-[0.7rem] text-ink-faint">{String(i + 1).padStart(2, "0")}</span>
                <div>
                  <h3 className="font-serif text-lg leading-snug text-ink">{d.title}</h3>
                  <p className="mt-1 font-serif text-[0.97rem] leading-relaxed text-ink-muted">{d.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="stack" className="grid gap-8 border-t border-rule pt-8 md:grid-cols-2">
          <div className="space-y-3">
            <h2 id="stack" className="kicker">
              Built with
            </h2>
            <p className="font-serif text-ink-muted">
              Python, LangGraph, Gemini, Tavily, ChromaDB and FastAPI on the backend; Next.js, TypeScript and
              Tailwind on the front. Prompts are versioned files, and every agent uses structured output.
            </p>
          </div>
          <div className="space-y-3">
            <h2 className="kicker">Related</h2>
            <p className="font-serif text-ink-muted">
              CiteCheck follows NS-Fact, a neuro-symbolic medical claim verifier built on a biomedical
              knowledge graph. Both are about language-model systems that check their own output, and measure
              it. Source code and results are on{" "}
              <a href="https://github.com/Narwinh/citecheck" target="_blank" rel="noreferrer">
                GitHub
              </a>
              ; more work on the{" "}
              <a href="https://narwinh.github.io" target="_blank" rel="noreferrer">
                portfolio
              </a>
              .
            </p>
            <p className="font-serif text-sm text-ink-faint italic">
              The pipeline idea (search, read, answer with numbered citations) was inspired by the open-source
              clarity-ai / perplexity-ai-clone projects. No code was copied.
            </p>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
