/**
 * Hook for fetching a single article with connections and timeline
 */

import { useState, useEffect, useCallback } from 'react';
import { articlesApi } from '../services/articles';
import { ApiError } from '../services/api';
import type { Article, GraphVisualization, StoryTimeline } from '../types';

export interface UseArticleResult {
  article: Article | null;
  connections: GraphVisualization | null;
  timeline: StoryTimeline | null;
  isLoading: boolean;
  error: ApiError | Error | null;
  refetch: () => Promise<void>;
}

export function useArticle(articleId: string | undefined): UseArticleResult {
  const [article, setArticle] = useState<Article | null>(null);
  const [connections, setConnections] = useState<GraphVisualization | null>(null);
  const [timeline, setTimeline] = useState<StoryTimeline | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!articleId) return;

    setIsLoading(true);
    setError(null);

    try {
      // Fetch all data in parallel for better performance
      const [articleData, connectionsData, timelineData] = await Promise.all([
        articlesApi.getById(articleId),
        articlesApi.getConnections(articleId, 2),
        articlesApi.getTimeline(articleId),
      ]);

      setArticle(articleData);
      setConnections(connectionsData);
      setTimeline(timelineData);
    } catch (err) {
      const apiError = err instanceof Error ? err : new Error(String(err));
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  }, [articleId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    article,
    connections,
    timeline,
    isLoading,
    error,
    refetch: fetchData,
  };
}

/**
 * Hook for fetching only article connections (for graph display)
 */
export function useArticleConnections(
  articleId: string | undefined,
  depth: number = 2
): {
  connections: GraphVisualization | null;
  isLoading: boolean;
  error: ApiError | Error | null;
  refetch: () => Promise<void>;
} {
  const [connections, setConnections] = useState<GraphVisualization | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!articleId) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await articlesApi.getConnections(articleId, depth);
      setConnections(data);
    } catch (err) {
      const apiError = err instanceof Error ? err : new Error(String(err));
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  }, [articleId, depth]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    connections,
    isLoading,
    error,
    refetch: fetchData,
  };
}
