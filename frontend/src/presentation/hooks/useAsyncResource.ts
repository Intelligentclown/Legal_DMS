import { useEffect, useRef, useState } from "react";

export interface AsyncResource<T> {
  data: T | null;
  /**
   * The raw failure, left unflattened on purpose: `ErrorMessage` decides how to
   * present an `HttpError`'s product-level message versus a transport failure.
   */
  error: unknown;
  isLoading: boolean;
  reload: () => void;
}

interface ResourceState<T> {
  /** The request this state belongs to; null until the first one settles. */
  key: string | null;
  data: T | null;
  error: unknown;
}

/**
 * Runs an async read and exposes its loading/error/data state.
 *
 * `key` identifies the request: change it to refetch (for example when a
 * paginated list moves to another page), and `reload` refetches the current
 * key after a mutation. Settled state is only ever read when it belongs to the
 * request in flight, so a stale response from a superseded request is never
 * shown while the new one is still loading, and there is no state write during
 * the effect body. The loader is read through a ref, so it may be an inline
 * closure over current props without becoming a dependency.
 */
export function useAsyncResource<T>(key: string, load: () => Promise<T>): AsyncResource<T> {
  const [state, setState] = useState<ResourceState<T>>({ key: null, data: null, error: null });
  const [reloadToken, setReloadToken] = useState(0);
  const loadRef = useRef(load);

  useEffect(() => {
    loadRef.current = load;
  });

  const requestKey = `${key}#${reloadToken}`;

  useEffect(() => {
    let cancelled = false;

    void loadRef.current().then(
      (data) => {
        if (!cancelled) {
          setState({ key: requestKey, data, error: null });
        }
      },
      (error: unknown) => {
        if (!cancelled) {
          setState({ key: requestKey, data: null, error });
        }
      },
    );

    return () => {
      cancelled = true;
    };
  }, [requestKey]);

  const isCurrent = state.key === requestKey;

  return {
    data: isCurrent ? state.data : null,
    error: isCurrent ? state.error : null,
    isLoading: !isCurrent,
    reload: () => setReloadToken((token) => token + 1),
  };
}
