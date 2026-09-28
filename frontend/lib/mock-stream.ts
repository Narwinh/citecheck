// A scripted event stream for building the UI without calling the backend.
// Passages are written for this mock (not copied from real sites) and use
// example.* domains. The script exercises every claim state: supported,
// partial -> rewritten, and unsupported -> removed.

import type { PassageCard, ResearchEvent } from "./types";

export const MOCK_QUESTION = "How do honeybees tell each other where to find food?";

const P = (id: number, domain: string, title: string, text: string): PassageCard => ({
  id,
  url: `https://${domain}/articles/${id}`,
  title,
  domain,
  favicon: null,
  snippet: text.slice(0, 200).replace(/\s\S*$/, "") + "…",
  text,
});

export const MOCK_PASSAGES: PassageCard[] = [
  P(
    1,
    "apiary-notes.example",
    "The waggle dance, explained",
    "A forager that finds a rich patch of flowers returns to the hive and performs the waggle dance on the vertical comb. The angle of the straight waggle run, measured from vertical, matches the angle between the sun and the food source. Nestmates follow the dancer and read the direction from it.",
  ),
  P(
    2,
    "field-biology.example",
    "Distance coding in honeybee dances",
    "Experiments with feeders placed at known distances show that the waggle run lasts longer when the food is farther away. Roughly, each second of waggling corresponds to several hundred metres of flight, although the exact calibration varies between colonies and landscapes.",
  ),
  P(
    3,
    "beekeeping-basics.example",
    "Round dances and nearby food",
    "When food is close to the hive, foragers perform a simpler round dance: they circle one way and then the other without a clear waggle run. The round dance tells recruits that food is nearby, but it carries little information about direction.",
  ),
  P(
    4,
    "history-of-science.example",
    "Karl von Frisch and the dance language",
    "The Austrian ethologist Karl von Frisch spent decades studying how honeybees communicate. His careful feeder experiments showed that the dance encodes information about food, an idea that was controversial when he first proposed it.",
  ),
  P(
    5,
    "pollinator-lab.example",
    "Scent and recruitment",
    "Dancers carry the scent of the flowers they visited on their bodies, and recruits learn this odour while following the dance. Once outside, the recruits use the remembered scent to pick out the right flowers near the indicated location.",
  ),
];

type Step = [delayMs: number, event: ResearchEvent];

const claims = [
  { id: 1, text: "Honeybees communicate the location of food through the waggle dance.", citation_ids: [1] },
  {
    id: 2,
    text: "The angle of the waggle run relative to vertical encodes the direction of the food relative to the sun.",
    citation_ids: [1],
  },
  {
    id: 3,
    text: "Longer waggle runs signal that the food source is farther from the hive.",
    citation_ids: [2],
  },
  {
    id: 4,
    text: "Bees switch to a round dance for food sources closer than about 50 metres.",
    citation_ids: [3],
  },
  {
    id: 5,
    text: "Karl von Frisch received the Nobel Prize in 1973 for decoding the dance.",
    citation_ids: [4],
  },
  {
    id: 6,
    text: "Dancers also share the scent of the flowers they visited, which helps recruits find them.",
    citation_ids: [5],
  },
];

export const MOCK_SCRIPT: Step[] = [
  [300, { event: "stage", data: { agent: "planner", status: "start" } }],
  [
    900,
    {
      event: "subqueries",
      data: { items: ["honeybee waggle dance direction distance", "honeybee round dance scent recruitment"] },
    },
  ],
  [150, { event: "stage", data: { agent: "planner", status: "done", ms: 1043 } }],
  [100, { event: "stage", data: { agent: "retriever", status: "start" } }],
  [2200, { event: "sources", data: { passages: MOCK_PASSAGES } }],
  [100, { event: "stage", data: { agent: "retriever", status: "done", ms: 2291 } }],
  [100, { event: "stage", data: { agent: "writer", status: "start" } }],
  [3200, { event: "draft", data: { status: "answered", missing: null, claims } }],
  [100, { event: "stage", data: { agent: "writer", status: "done", ms: 3284 } }],
  [100, { event: "stage", data: { agent: "verifier", status: "start" } }],
  [
    1800,
    {
      event: "verdict",
      data: {
        claim_id: 1,
        label: "SUPPORTED",
        evidence_span:
          "A forager that finds a rich patch of flowers returns to the hive and performs the waggle dance on the vertical comb.",
        rationale: "The passage states that foragers perform the waggle dance after finding food.",
      },
    },
  ],
  [
    250,
    {
      event: "verdict",
      data: {
        claim_id: 2,
        label: "SUPPORTED",
        evidence_span:
          "The angle of the straight waggle run, measured from vertical, matches the angle between the sun and the food source.",
        rationale: "Directly stated.",
      },
    },
  ],
  [
    250,
    {
      event: "verdict",
      data: {
        claim_id: 3,
        label: "SUPPORTED",
        evidence_span: "the waggle run lasts longer when the food is farther away",
        rationale: "The passage links longer waggle runs to greater distance.",
      },
    },
  ],
  [
    250,
    {
      event: "verdict",
      data: {
        claim_id: 4,
        label: "PARTIAL",
        evidence_span: "When food is close to the hive, foragers perform a simpler round dance",
        rationale: "The round dance for nearby food is stated, but the 50-metre threshold is not.",
      },
    },
  ],
  [
    250,
    {
      event: "verdict",
      data: {
        claim_id: 5,
        label: "UNSUPPORTED",
        evidence_span: null,
        rationale: "The passage describes von Frisch's research but never mentions a Nobel Prize or 1973.",
      },
    },
  ],
  [
    250,
    {
      event: "verdict",
      data: {
        claim_id: 6,
        label: "SUPPORTED",
        evidence_span:
          "Dancers carry the scent of the flowers they visited on their bodies, and recruits learn this odour while following the dance.",
        rationale: "Directly stated.",
      },
    },
  ],
  [100, { event: "stage", data: { agent: "verifier", status: "done", ms: 3162 } }],
  [100, { event: "stage", data: { agent: "reviser", status: "start" } }],
  [
    2600,
    {
      event: "revision",
      data: {
        claim_id: 4,
        action: "rewritten",
        new_text: "For food close to the hive, bees perform a simpler round dance instead.",
        new_citation_ids: [3],
      },
    },
  ],
  [
    150,
    {
      event: "verdict",
      data: {
        claim_id: 4,
        label: "SUPPORTED",
        evidence_span: "When food is close to the hive, foragers perform a simpler round dance",
        rationale: "The rewritten claim matches the passage without the unsupported distance.",
      },
    },
  ],
  [150, { event: "revision", data: { claim_id: 5, action: "removed" } }],
  [100, { event: "stage", data: { agent: "reviser", status: "done", ms: 2987 } }],
  [
    200,
    {
      event: "final",
      data: {
        status: "answered",
        missing: null,
        claims: [claims[0], claims[1], claims[2],
          { id: 4, text: "For food close to the hive, bees perform a simpler round dance instead.", citation_ids: [3] },
          claims[5]],
        stats: {
          claims: 6,
          supported: 4,
          partial: 1,
          unsupported: 1,
          revised: 1,
          removed: 1,
          final_claims: 5,
          total_ms: 14212,
          tokens: 9315,
        },
      },
    },
  ],
];

/** Replay the script with its delays. `speed` > 1 plays faster. */
export async function* mockStream(speed = 1, signal?: AbortSignal): AsyncGenerator<ResearchEvent> {
  for (const [delay, event] of MOCK_SCRIPT) {
    await new Promise((resolve) => setTimeout(resolve, delay / speed));
    if (signal?.aborted) return;
    yield event;
  }
}
