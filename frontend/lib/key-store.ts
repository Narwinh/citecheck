// The visitor's own Gemini key, if they provide one. Held in memory only:
// never written to localStorage, cookies, or the URL, and gone on reload.

import { useSyncExternalStore } from "react";

let key = "";
const listeners = new Set<() => void>();

export function setApiKey(value: string) {
  key = value.trim();
  listeners.forEach((l) => l());
}

export function getApiKey() {
  return key;
}

export function useApiKey() {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    getApiKey,
    () => "",
  );
}
