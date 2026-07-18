export function subscribeToUpdates(
  target: EventTarget,
  listener: EventListener,
): () => void {
  target.addEventListener("update", listener);
  return () => target.removeEventListener("update", listener);
}
