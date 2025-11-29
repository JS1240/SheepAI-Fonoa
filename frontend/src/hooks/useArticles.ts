/**
 * Hook for fetching article list with filters
 */

import { useMemo, useState, useCallback } from 'react';
import { useApi, UseApiResult } from './useApi';
import { articlesApi, ArticleListParams } from '../services/articles';
import type { ArticleSummary } from '../types';

export interface UseArticlesOptions {
  initialQuery?: string;
  initialCategory?: string;
  initialDays?: number;
  limit?: number;
}

export interface UseArticlesResult extends UseApiResult<ArticleSummary[]> {
  query: string;
  setQuery: (query: string) => void;
  category: string;
  setCategory: (category: string) => void;
  days: number;
  setDays: (days: number) => void;
}

export function useArticles(options: UseArticlesOptions = {}): UseArticlesResult {
  const {
    initialQuery = '',
    initialCategory = '',
    initialDays = 7,
    limit = 20,
  } = options;

  const [query, setQuery] = useState(initialQuery);
  const [category, setCategory] = useState(initialCategory);
  const [days, setDays] = useState(initialDays);

  // Debounced query value - using simple approach for hackathon
  const [debouncedQuery, setDebouncedQuery] = useState(query);

  // Simple debounce for search query
  const handleSetQuery = useCallback((newQuery: string) => {
    setQuery(newQuery);
    // Debounce the actual API call
    const timeoutId = setTimeout(() => {
      setDebouncedQuery(newQuery);
    }, 300);
    return () => clearTimeout(timeoutId);
  }, []);

  const params: ArticleListParams = useMemo(() => ({
    q: debouncedQuery || undefined,
    category: category || undefined,
    days,
    limit,
  }), [debouncedQuery, category, days, limit]);

  const fetcher = useCallback(() => articlesApi.list(params), [params]);

  const apiResult = useApi<ArticleSummary[]>(
    fetcher,
    [debouncedQuery, category, days, limit]
  );

  return {
    ...apiResult,
    query,
    setQuery: handleSetQuery,
    category,
    setCategory,
    days,
    setDays,
  };
}
