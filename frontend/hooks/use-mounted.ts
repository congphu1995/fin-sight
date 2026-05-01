import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

// True after hydration. Useful for components that render different content on
// the server vs. the client (theme, localStorage-backed lists). Using
// useSyncExternalStore avoids the `react-hooks/set-state-in-effect` lint rule
// flagging the typical `useEffect(() => setMounted(true), [])` pattern.
export function useMounted(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
