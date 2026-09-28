import type { Mode } from "./types";

export function researchHref(question: string, mode: Mode) {
  return `/research?q=${encodeURIComponent(question.trim())}&mode=${mode}`;
}
