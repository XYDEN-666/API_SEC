import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

export interface AsyncData<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
  setData: (value: T) => void;
}

/**
 * Load data for a page, exposing loading/error state plus a `reload` trigger
 * for retry buttons. Late responses from superseded loads are discarded.
 */
export function useAsyncData<T>(
  loader: () => Promise<T>,
  deps: readonly unknown[],
  options: { enabled?: boolean } = {},
): AsyncData<T> {
  const enabled = options.enabled ?? true;
  const [data, setDataState] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [nonce, setNonce] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    loaderRef
      .current()
      .then((value) => {
        if (!cancelled) {
          setDataState(value);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError || err instanceof Error
              ? err.message
              : "Unexpected error",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
    // `deps` is spread deliberately: callers pass the identifiers their loader
    // closes over, and the nonce forces a manual reload.
  }, [enabled, nonce, ...deps]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);
  const setData = useCallback((value: T) => {
    setDataState(value);
    setError(null);
  }, []);

  return { data, error, loading, reload, setData };
}
