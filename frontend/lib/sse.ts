// POST-capable SSE client. EventSource only supports GET, so we read the
// response body stream ourselves and split it into `event:` / `data:` blocks.

import type { Mode, ResearchEvent } from "./types";

export class RequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly retryAfterS?: number,
  ) {
    super(message);
  }
}

export function parseBlock(block: string): ResearchEvent | null {
  let event = "";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith(":")) continue; // heartbeat comment
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  if (!event || data.length === 0) return null;
  return { event, data: JSON.parse(data.join("\n")) } as ResearchEvent;
}

export async function* streamResearch(opts: {
  apiUrl: string;
  question: string;
  mode: Mode;
  apiKey?: string;
  signal?: AbortSignal;
}): AsyncGenerator<ResearchEvent> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (opts.apiKey) headers["X-Gemini-Key"] = opts.apiKey;

  const res = await fetch(`${opts.apiUrl}/api/ask`, {
    method: "POST",
    headers,
    body: JSON.stringify({ question: opts.question, mode: opts.mode }),
    signal: opts.signal,
  });
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : "Request failed.";
    throw new RequestError(detail, res.status, body.retry_after_s);
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value.replace(/\r\n/g, "\n");
    let cut: number;
    while ((cut = buffer.indexOf("\n\n")) !== -1) {
      const parsed = parseBlock(buffer.slice(0, cut));
      buffer = buffer.slice(cut + 2);
      if (parsed) yield parsed;
    }
  }
}
