// Folds the SSE event stream into the state the research view renders.

import type {
  AgentName,
  Claim,
  FinalStats,
  PassageCard,
  ResearchEvent,
  Verdict,
  WriterStatus,
} from "./types";

export const AGENTS: AgentName[] = ["planner", "retriever", "writer", "verifier", "reviser"];

export type AgentStatus = "idle" | "running" | "done" | "skipped" | "failed";

export type ClaimState =
  | "verifying"
  | "supported"
  | "partial"
  | "unsupported"
  | "rewritten"
  | "removed";

export interface ClaimView extends Claim {
  state: ClaimState;
  verdict?: Verdict;
  /** The writer's original sentence, kept when the reviser rewrote it. */
  original?: Claim & { verdict?: Verdict };
}

export interface ResearchState {
  phase: "idle" | "running" | "done" | "error";
  agents: Record<AgentName, { status: AgentStatus; ms?: number }>;
  subQueries: string[];
  sources: PassageCard[];
  claims: ClaimView[];
  writerStatus?: WriterStatus;
  missing: string | null;
  stats?: FinalStats;
  error?: { code: string; message: string };
}

export function initialResearchState(): ResearchState {
  return {
    phase: "idle",
    agents: Object.fromEntries(AGENTS.map((a) => [a, { status: "idle" }])) as ResearchState["agents"],
    subQueries: [],
    sources: [],
    claims: [],
    missing: null,
  };
}

const LABEL_STATE: Record<Verdict["label"], ClaimState> = {
  SUPPORTED: "supported",
  PARTIAL: "partial",
  UNSUPPORTED: "unsupported",
};

export function reduce(state: ResearchState, e: ResearchEvent): ResearchState {
  switch (e.event) {
    case "stage": {
      const agents = { ...state.agents };
      agents[e.data.agent] =
        e.data.status === "start" ? { status: "running" } : { status: "done", ms: e.data.ms };
      return { ...state, phase: "running", agents };
    }
    case "subqueries":
      return { ...state, subQueries: e.data.items };
    case "sources":
      return { ...state, sources: e.data.passages };
    case "draft":
      return {
        ...state,
        writerStatus: e.data.status,
        missing: e.data.missing,
        claims: e.data.claims.map((c) => ({ ...c, state: "verifying" })),
      };
    case "verdict":
      return {
        ...state,
        claims: state.claims.map((c) => {
          if (c.id !== e.data.claim_id) return c;
          // A verdict after a rewrite grades the new sentence; keep the "rewritten" state.
          if (c.state === "rewritten") return { ...c, verdict: e.data };
          return { ...c, verdict: e.data, state: LABEL_STATE[e.data.label] };
        }),
      };
    case "revision":
      return {
        ...state,
        claims: state.claims.map((c) => {
          if (c.id !== e.data.claim_id) return c;
          if (e.data.action === "removed") return { ...c, state: "removed" };
          return {
            ...c,
            original: { id: c.id, text: c.text, citation_ids: c.citation_ids, verdict: c.verdict },
            text: e.data.new_text ?? c.text,
            citation_ids: e.data.new_citation_ids ?? c.citation_ids,
            state: "rewritten",
            verdict: undefined,
          };
        }),
      };
    case "final": {
      const agents = { ...state.agents };
      for (const a of AGENTS) if (agents[a].status === "idle") agents[a] = { status: "skipped" };
      return {
        ...state,
        phase: "done",
        agents,
        writerStatus: e.data.status,
        missing: e.data.missing,
        stats: e.data.stats,
      };
    }
    case "error": {
      const agents = { ...state.agents };
      for (const a of AGENTS) if (agents[a].status === "running") agents[a] = { status: "failed" };
      return { ...state, phase: "error", agents, error: e.data };
    }
  }
}

/** Passage ids cited by any claim still shown (not removed). */
export function citedIds(claims: ClaimView[]): Set<number> {
  return new Set(claims.filter((c) => c.state !== "removed").flatMap((c) => c.citation_ids));
}
