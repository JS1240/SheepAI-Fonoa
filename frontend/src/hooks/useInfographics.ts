/**
 * Hook for managing infographics for an article
 */

import { useState, useEffect, useCallback } from 'react';
import { infographicsApi } from '../services/infographics';
import { ApiError } from '../services/api';
import type { Infographic, InfographicType } from '../types';

interface InfographicState {
  url: string | null;
  isGenerating: boolean;
  error: string | null;
}

export interface UseInfographicsResult {
  infographics: Record<InfographicType, InfographicState>;
  isLoading: boolean;
  error: ApiError | Error | null;
  generate: (type: InfographicType, forceRegenerate?: boolean) => Promise<Infographic | null>;
  refetch: () => Promise<void>;
}

const INFOGRAPHIC_TYPES: InfographicType[] = ['threat_summary', 'timeline', 'knowledge_graph'];

const createInitialState = (): Record<InfographicType, InfographicState> => ({
  threat_summary: { url: null, isGenerating: false, error: null },
  timeline: { url: null, isGenerating: false, error: null },
  knowledge_graph: { url: null, isGenerating: false, error: null },
});

export function useInfographics(articleId: string | undefined): UseInfographicsResult {
  const [infographics, setInfographics] = useState<Record<InfographicType, InfographicState>>(
    createInitialState()
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | Error | null>(null);

  // Fetch existing infographics
  const fetchExisting = useCallback(async () => {
    if (!articleId) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await infographicsApi.list(articleId);

      // Update state with existing infographics
      setInfographics((prev) => {
        const newState = { ...prev };
        for (const type of INFOGRAPHIC_TYPES) {
          if (data.infographics[type]) {
            newState[type] = {
              ...newState[type],
              url: data.infographics[type],
              error: null,
            };
          }
        }
        return newState;
      });
    } catch (err) {
      const apiError = err instanceof Error ? err : new Error(String(err));
      setError(apiError);
    } finally {
      setIsLoading(false);
    }
  }, [articleId]);

  // Generate an infographic
  const generate = useCallback(
    async (type: InfographicType, forceRegenerate: boolean = false): Promise<Infographic | null> => {
      if (!articleId) return null;

      // Set generating state for this type
      setInfographics((prev) => ({
        ...prev,
        [type]: { ...prev[type], isGenerating: true, error: null },
      }));

      try {
        const response = await infographicsApi.generate(articleId, type, forceRegenerate);

        // Update state with the new URL
        setInfographics((prev) => ({
          ...prev,
          [type]: {
            url: response.infographic.public_url || null,
            isGenerating: false,
            error: null,
          },
        }));

        return response.infographic;
      } catch (err) {
        const errorMessage = err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to generate infographic';

        setInfographics((prev) => ({
          ...prev,
          [type]: {
            ...prev[type],
            isGenerating: false,
            error: errorMessage,
          },
        }));

        return null;
      }
    },
    [articleId]
  );

  // Fetch existing infographics on mount
  useEffect(() => {
    fetchExisting();
  }, [fetchExisting]);

  return {
    infographics,
    isLoading,
    error,
    generate,
    refetch: fetchExisting,
  };
}
