/**
 * Generic API hook for data fetching with loading and error states
 */

import { useState, useEffect, useCallback } from 'react';
import { ApiError } from '../services/api';

export interface UseApiResult<T> {
  data: T | null;
  isLoading: boolean;
  error: ApiError | Error | null;
  refetch: () => Promise<void>;
}

export interface UseApiOptions {
  enabled?: boolean;
  onSuccess?: <T>(data: T) => void;
  onError?: (error: ApiError | Error) => void;
}

/**
 * Generic hook for API calls with automatic fetching
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  options: UseApiOptions = {}
): UseApiResult<T> {
  const { enabled = true, onSuccess, onError } = options;

  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState<ApiError | Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await fetcher();
      setData(result);
      onSuccess?.(result);
    } catch (err) {
      const apiError = err instanceof Error ? err : new Error(String(err));
      setError(apiError);
      onError?.(apiError);
    } finally {
      setIsLoading(false);
    }
  }, [fetcher, enabled, onSuccess, onError]);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchData,
  };
}

/**
 * Hook for lazy API calls (triggered manually)
 */
export function useLazyApi<T, P = void>(
  fetcher: (params: P) => Promise<T>
): [
  (params: P) => Promise<T | null>,
  UseApiResult<T>
] {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | Error | null>(null);

  const execute = useCallback(async (params: P): Promise<T | null> => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await fetcher(params);
      setData(result);
      return result;
    } catch (err) {
      const apiError = err instanceof Error ? err : new Error(String(err));
      setError(apiError);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [fetcher]);

  const refetch = useCallback(async () => {
    // For lazy queries, refetch does nothing without params
  }, []);

  return [
    execute,
    { data, isLoading, error, refetch },
  ];
}
