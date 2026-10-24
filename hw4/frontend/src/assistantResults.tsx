import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { PageResults } from "./api";

/**
 * Products the shopping assistant found, shared between the chat panel (which receives them)
 * and the Products page (which shows them as cards). Kept in memory for instant display; the
 * search itself is also in the page address (`q`), so after a refresh the Products page fetches
 * the same results again (Problem 9).
 */
interface AssistantResultsState {
  results: PageResults | null;
  show: (results: PageResults) => void;
  clear: () => void;
}

const AssistantResultsContext = createContext<AssistantResultsState | null>(null);

export function AssistantResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<PageResults | null>(null);
  const show = useCallback((r: PageResults) => setResults(r), []);
  const clear = useCallback(() => setResults(null), []);
  const value = useMemo(() => ({ results, show, clear }), [results, show, clear]);
  return <AssistantResultsContext.Provider value={value}>{children}</AssistantResultsContext.Provider>;
}

export function useAssistantResults(): AssistantResultsState {
  const value = useContext(AssistantResultsContext);
  if (!value) throw new Error("useAssistantResults must be used inside <AssistantResultsProvider>");
  return value;
}

/** The Products page address that shows the assistant's results for one search. */
export const assistantViewUrl = (query: string) => `/products?view=assistant&q=${encodeURIComponent(query)}`;
