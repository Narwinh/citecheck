export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** True when the backend answers /api/health within the timeout. */
export async function isBackendAwake(timeoutMs = 4000): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/api/health`, { signal: AbortSignal.timeout(timeoutMs) });
    return res.ok;
  } catch {
    return false;
  }
}

export interface Example {
  question: string;
  category: string;
}

export async function fetchExamples(): Promise<Example[]> {
  const res = await fetch(`${API_URL}/api/examples`, { signal: AbortSignal.timeout(4000) });
  if (!res.ok) throw new Error("examples unavailable");
  return res.json();
}
