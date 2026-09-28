// The pipeline as a diagram. SVG on wide screens (themed through CSS
// variables); a vertical list on phones, where a wide diagram would be tiny.

const NODES = [
  { id: "question", x: 16, w: 112, title: "Question", sub: ["from the reader"] },
  { id: "planner", x: 158, w: 124, title: "Planner", sub: ["1-4 web searches"] },
  { id: "retriever", x: 312, w: 168, title: "Retriever", sub: ["Tavily search", "Gemini embeddings", "in-memory Chroma"] },
  { id: "writer", x: 510, w: 124, title: "Writer", sub: ["sentences, each", "citing passages"] },
  { id: "verifier", x: 664, w: 130, title: "Verifier", sub: ["reads the cited", "passage only"] },
  { id: "answer", x: 824, w: 120, title: "Answer", sub: ["with verdicts", "and evidence"] },
];

const Y = 64;
const H = 96;

export function ArchitectureDiagram() {
  return (
    <figure className="space-y-3">
      <svg
        viewBox="0 0 960 300"
        role="img"
        aria-labelledby="arch-title arch-desc"
        className="hidden w-full md:block"
      >
        <title id="arch-title">CiteCheck pipeline</title>
        <desc id="arch-desc">
          Question to planner to retriever to writer to verifier to answer. Claims the verifier rejects go to
          the reviser, which rewrites or removes them, and rewrites are checked once more.
        </desc>
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" style={{ fill: "var(--ink-muted)" }} />
          </marker>
        </defs>

        {NODES.slice(0, -1).map((n, i) => {
          const next = NODES[i + 1];
          return (
            <line
              key={n.id}
              x1={n.x + n.w}
              y1={Y + H / 2}
              x2={next.x - 4}
              y2={Y + H / 2}
              style={{ stroke: "var(--ink-muted)", strokeWidth: 1.5 }}
              markerEnd="url(#arrow)"
            />
          );
        })}

        {NODES.map((n) => {
          const accent = n.id === "verifier";
          return (
            <g key={n.id}>
              <rect
                x={n.x}
                y={Y}
                width={n.w}
                height={H}
                rx={6}
                style={{
                  fill: accent ? "var(--accent-soft)" : "var(--paper-raised)",
                  stroke: accent ? "var(--accent)" : "var(--rule-strong)",
                  strokeWidth: accent ? 1.5 : 1,
                }}
              />
              <text x={n.x + 12} y={Y + 26} className="font-mono" style={{ fill: "var(--ink)", fontSize: 12, letterSpacing: "0.08em" }}>
                {n.title.toUpperCase()}
              </text>
              {n.sub.map((line, i) => (
                <text key={line} x={n.x + 12} y={Y + 50 + i * 16} className="font-serif" style={{ fill: "var(--ink-muted)", fontSize: 13 }}>
                  {line}
                </text>
              ))}
            </g>
          );
        })}

        {/* reviser loop under the verifier */}
        <rect x={664} y={206} width={130} height={66} rx={6} style={{ fill: "var(--paper-raised)", stroke: "var(--rule-strong)" }} />
        <text x={676} y={230} className="font-mono" style={{ fill: "var(--ink)", fontSize: 12, letterSpacing: "0.08em" }}>
          REVISER
        </text>
        <text x={676} y={252} className="font-serif" style={{ fill: "var(--ink-muted)", fontSize: 13 }}>
          rewrite or remove
        </text>
        <path d="M700,160 L700,202" style={{ stroke: "var(--ink-muted)", strokeWidth: 1.5, fill: "none" }} markerEnd="url(#arrow)" />
        <path d="M758,206 L758,164" style={{ stroke: "var(--ink-muted)", strokeWidth: 1.5, fill: "none" }} markerEnd="url(#arrow)" />
        <text x={608} y={188} className="font-mono" style={{ fill: "var(--ink-faint)", fontSize: 11 }}>
          rejected
        </text>
        <text x={766} y={188} className="font-mono" style={{ fill: "var(--ink-faint)", fontSize: 11 }}>
          re-check once
        </text>

        <text x={16} y={36} className="font-mono" style={{ fill: "var(--ink-faint)", fontSize: 11, letterSpacing: "0.08em" }}>
          LANGGRAPH STATE GRAPH · EVERY STEP STREAMS EVENTS TO THE BROWSER
        </text>
      </svg>

      <ol className="space-y-0 md:hidden" aria-label="CiteCheck pipeline">
        {[...NODES.slice(0, 5), { id: "reviser", title: "Reviser", sub: ["rewrites or removes rejected claims, then re-checks once"] }, NODES[5]].map(
          (n, i, all) => (
            <li key={n.id} className="relative flex gap-3 pb-4">
              {i < all.length - 1 && <span aria-hidden className="absolute top-3 left-[5px] h-full w-px bg-rule-strong" />}
              <span
                aria-hidden
                className={`relative mt-1 size-[11px] shrink-0 rounded-full border ${n.id === "verifier" ? "border-accent bg-accent-soft" : "border-rule-strong bg-paper-raised"}`}
              />
              <div>
                <p className="font-mono text-[0.7rem] tracking-[0.08em] text-ink uppercase">{n.title}</p>
                <p className="font-serif text-sm text-ink-muted">{n.sub.join(" · ")}</p>
              </div>
            </li>
          ),
        )}
      </ol>
      <figcaption className="font-serif text-sm text-ink-muted italic">
        The revision loop runs at most once, to bound latency and cost.
      </figcaption>
    </figure>
  );
}
