import { type Dispatch, type SetStateAction, useEffect, useRef, useState } from "react";

/**
 * A field that is edited here and stored there.
 *
 * Every save echoes a fresh resource back into the query cache — and so does every
 * *other* save on the same record, because a mutation invalidates the whole thing.
 * Adopting that echo unconditionally erased whatever had been typed since the request
 * went out: the surname came back from the server and the patronymic being typed
 * meanwhile disappeared, which is what made these forms feel like they fight back.
 *
 * So the stored value seeds the field, and is adopted again whenever it really
 * changes — but only into a field that still holds exactly what the server last sent.
 * An unsaved edit always outranks the echo. The new value is remembered either way,
 * so once that edit is saved the two are in step again and the next outside change
 * (another tab, an organizer's correction) lands normally.
 *
 * @param server The stored value, mapped to the shape the field renders.
 * @param isSame Value equality — the identity of `server` is meaningless, since a
 *   refetch rebuilds it on every render.
 */
export function useServerDraft<T>(
  server: T,
  isSame: (a: T, b: T) => boolean,
): [T, Dispatch<SetStateAction<T>>] {
  const [draft, setDraft] = useState(server);

  /** What the server last told us: what an untouched field is showing. */
  const known = useRef(server);
  const draftRef = useRef(draft);
  draftRef.current = draft;
  const isSameRef = useRef(isSame);
  isSameRef.current = isSame;

  useEffect(() => {
    const previous = known.current;
    if (isSameRef.current(previous, server)) {
      return;
    }
    known.current = server;
    if (!isSameRef.current(draftRef.current, previous)) {
      return;
    }
    setDraft(server);
  }, [server]);

  return [draft, setDraft];
}
