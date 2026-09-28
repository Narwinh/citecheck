// Mirrors the backend SSE events (backend/app/graph.py, CLAUDE.md Section 5).

export type AgentName = "planner" | "retriever" | "writer" | "verifier" | "reviser";
export type Label = "SUPPORTED" | "PARTIAL" | "UNSUPPORTED";
export type Mode = "strict" | "lenient";
export type WriterStatus = "answered" | "partial" | "unanswerable";

export interface PassageCard {
  id: number;
  url: string;
  title: string;
  domain: string;
  favicon: string | null;
  snippet: string;
  text: string;
}

export interface Claim {
  id: number;
  text: string;
  citation_ids: number[];
}

export interface Verdict {
  claim_id: number;
  label: Label;
  evidence_span: string | null;
  rationale: string;
  downgraded?: boolean;
}

export interface Revision {
  claim_id: number;
  action: "rewritten" | "removed";
  new_text?: string;
  new_citation_ids?: number[];
}

export interface FinalStats {
  claims: number;
  supported: number;
  partial: number;
  unsupported: number;
  revised: number;
  removed: number;
  final_claims: number;
  total_ms: number;
  tokens: number;
}

export type ResearchEvent =
  | { event: "stage"; data: { agent: AgentName; status: "start" | "done"; ms?: number } }
  | { event: "subqueries"; data: { items: string[] } }
  | { event: "sources"; data: { passages: PassageCard[] } }
  | { event: "draft"; data: { status: WriterStatus; missing: string | null; claims: Claim[] } }
  | { event: "verdict"; data: Verdict }
  | { event: "revision"; data: Revision }
  | {
      event: "final";
      data: { status: WriterStatus; missing: string | null; claims: Claim[]; stats: FinalStats };
    }
  | { event: "error"; data: { code: "quota" | "unavailable" | "internal"; message: string } };
