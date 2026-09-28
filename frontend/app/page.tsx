import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { AskForm } from "@/components/ask-form";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { EXAMPLES } from "@/lib/examples";
import { researchHref } from "@/lib/links";

const STEPS = [
  { n: "01", name: "Planner", text: "Splits your question into focused web searches." },
  { n: "02", name: "Retriever", text: "Searches, reads the pages, and ranks the passages that matter." },
  { n: "03", name: "Writer", text: "Drafts the answer one sentence at a time, citing a passage for each." },
  { n: "04", name: "Verifier", text: "Reads every cited passage and checks it actually says so." },
];

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main className="relative z-10">
        <section className="mx-auto grid max-w-6xl gap-10 px-4 pt-14 pb-16 sm:px-8 lg:grid-cols-[minmax(0,1fr)_18rem] lg:pt-20">
          <div className="space-y-8">
            <div className="space-y-5">
              <p className="kicker">A verification-focused research assistant</p>
              <h1 className="font-serif text-[3rem] leading-[0.98] font-light tracking-[-0.025em] sm:text-7xl">
                Answers you can <em className="font-normal">check.</em>
              </h1>
              <p className="max-w-2xl font-serif text-xl leading-relaxed text-ink-muted">
                Every sentence cites a web source. Then a second agent reads that source and marks whether it
                really says so, fixing or removing the sentences it can&rsquo;t back up.
              </p>
            </div>
            <AskForm />
          </div>
          <aside className="space-y-3 self-end border-l border-rule pl-5 lg:mb-14">
            <p className="kicker">What you&rsquo;ll see</p>
            <ul className="space-y-2 font-serif text-[0.95rem] text-ink-muted">
              <li>
                <span className="text-ink underline decoration-supported/70 decoration-[1.5px] underline-offset-4">
                  Supported
                </span>{" "}
                sentences, underlined.
              </li>
              <li>
                <span className="text-ink underline decoration-partial decoration-dotted decoration-2 underline-offset-4">
                  Partly supported
                </span>{" "}
                ones, dotted.
              </li>
              <li>
                <span className="text-unsupported line-through decoration-unsupported/80">Unsupported</span> ones,
                struck out, then revised or removed.
              </li>
              <li>The exact quote behind each claim, on hover.</li>
            </ul>
            <Link href="/research?demo=1" className="inline-flex items-center gap-1 font-mono text-xs">
              Watch a recorded run <ArrowUpRight aria-hidden className="size-3" />
            </Link>
          </aside>
        </section>

        <section aria-labelledby="examples" className="border-t border-rule">
          <div className="mx-auto max-w-6xl px-4 py-12 sm:px-8">
            <h2 id="examples" className="kicker">
              Try one
            </h2>
            <ul className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {EXAMPLES.map((e) => (
                <li key={e.question}>
                  <Link
                    href={researchHref(e.question, "strict")}
                    className="group flex h-full flex-col justify-between gap-4 rounded-md border border-rule bg-paper-raised p-4 text-ink no-underline transition-colors hover:border-rule-strong"
                  >
                    <span className="font-serif text-[1.05rem] leading-snug">{e.question}</span>
                    <span className="flex items-center justify-between font-mono text-[0.66rem] tracking-wide text-ink-faint uppercase">
                      {e.category}
                      <ArrowUpRight
                        aria-hidden
                        className="size-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                      />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section aria-labelledby="how" className="border-t border-rule">
          <div className="mx-auto max-w-6xl px-4 py-12 sm:px-8">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h2 id="how" className="kicker">
                How it works
              </h2>
              <Link href="/about" className="font-mono text-xs">
                Architecture and design decisions
              </Link>
            </div>
            <ol className="mt-6 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
              {STEPS.map((s) => (
                <li key={s.n} className="border-t border-ink pt-3">
                  <p className="font-mono text-[0.7rem] text-ink-faint">{s.n}</p>
                  <p className="mt-1 font-mono text-xs tracking-[0.08em] text-ink uppercase">{s.name}</p>
                  <p className="mt-2 font-serif text-[0.95rem] leading-relaxed text-ink-muted">{s.text}</p>
                </li>
              ))}
            </ol>
            <p className="mt-8 max-w-2xl font-serif text-ink-muted">
              How much does the verifier help? It&rsquo;s measured, not claimed:{" "}
              <Link href="/eval">see the evaluation</Link>.
            </p>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
