"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import { API_URL, isBackendAwake } from "./api";
import { getApiKey } from "./key-store";
import { mockStream } from "./mock-stream";
import { initialResearchState, reduce, type ResearchState } from "./research";
import { RequestError, streamResearch } from "./sse";
import type { Mode, ResearchEvent } from "./types";

export type Connection =
  | { kind: "idle" }
  | { kind: "warming"; since: number }
  | { kind: "streaming" }
  | { kind: "done" }
  | { kind: "rate_limited"; retryAt: number; message: string }
  | { kind: "failed"; message: string };

const WARMUP_POLL_MS = 3000;
const WARMUP_LIMIT_MS = 150_000; // free Spaces can take a couple of minutes to wake

type Action = { type: "reset" } | { type: "event"; event: ResearchEvent };

function reducer(state: ResearchState, action: Action) {
  return action.type === "reset" ? initialResearchState() : reduce(state, action.event);
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function useResearch({ question, mode, demo }: { question: string; mode: Mode; demo: boolean }) {
  const [state, dispatch] = useReducer(reducer, undefined, initialResearchState);
  const [connection, setConnection] = useState<Connection>({ kind: "idle" });
  const abortRef = useRef<AbortController | null>(null);

  // Everything here happens after an await, so the effect below never sets
  // state synchronously. The view is keyed per question, so a first run
  // always starts from fresh state; retry() resets explicitly.
  const stream = useCallback(async (signal: AbortSignal) => {
    try {
      let events: AsyncGenerator<ResearchEvent>;
      if (demo) {
        events = mockStream(1, signal);
      } else {
        if (!(await isBackendAwake())) {
          const since = Date.now();
          setConnection({ kind: "warming", since });
          while (!(await isBackendAwake())) {
            if (signal.aborted) return;
            if (Date.now() - since > WARMUP_LIMIT_MS) {
              setConnection({ kind: "failed", message: "The research engine didn't wake up. Try again in a minute." });
              return;
            }
            await sleep(WARMUP_POLL_MS);
          }
        }
        // Checked before sending: React dev mode mounts effects twice, and the
        // first, cancelled run must not spend a question from the quota.
        if (signal.aborted) return;
        events = streamResearch({ apiUrl: API_URL, question, mode, apiKey: getApiKey() || undefined, signal });
      }

      let first = true;
      for await (const event of events) {
        if (signal.aborted) return;
        if (first) setConnection({ kind: "streaming" });
        first = false;
        dispatch({ type: "event", event });
      }
      if (!signal.aborted) setConnection({ kind: "done" });
    } catch (err) {
      if (signal.aborted) return;
      if (err instanceof RequestError && err.status === 429) {
        const wait = (err.retryAfterS ?? 60) * 1000;
        setConnection({ kind: "rate_limited", retryAt: Date.now() + wait, message: err.message });
      } else if (err instanceof RequestError) {
        setConnection({ kind: "failed", message: err.message });
      } else {
        setConnection({
          kind: "failed",
          message: "The connection to the research engine dropped before the answer finished.",
        });
      }
    }
  }, [question, mode, demo]);

  const start = useCallback(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    void stream(controller.signal);
    return controller;
  }, [stream]);

  useEffect(() => {
    // Subscribing to an external stream; every setState in stream() runs after an
    // await (in its callbacks), which the rule can't see through the call.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    const controller = start();
    return () => controller.abort();
  }, [start]);

  const retry = useCallback(() => {
    dispatch({ type: "reset" });
    setConnection({ kind: "idle" });
    start();
  }, [start]);

  return { state, connection, retry };
}
