/**
 * Session lifecycle events — a tiny synchronous pub/sub decoupling the HTTP
 * transport from React.
 *
 * The refresh hook (and the auth feature) live in the shared/api transport,
 * which must not import React or routing. When a refresh fails — the access
 * token expired and the rotating refresh token is gone or was reused/revoked
 * (API-001 §4.5) — the transport emits `session-expired`. The AuthProvider
 * subscribes and reacts (clears the session, routes to `/session-expired`),
 * keeping the transport framework-agnostic.
 */
export type SessionEvent = "session-expired";

type Listener = () => void;

const listeners = new Map<SessionEvent, Set<Listener>>();

/** Subscribe to a session event. Returns an unsubscribe function. */
export function onSessionEvent(event: SessionEvent, listener: Listener): () => void {
  const set = listeners.get(event) ?? new Set<Listener>();
  set.add(listener);
  listeners.set(event, set);
  return () => {
    set.delete(listener);
  };
}

/** Emit a session event to all current subscribers. */
export function emitSessionEvent(event: SessionEvent): void {
  const set = listeners.get(event);
  if (!set) {
    return;
  }
  for (const listener of set) {
    listener();
  }
}
