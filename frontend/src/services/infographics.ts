/**
 * Infographics API service
 */

import { get, post } from './api';
import type { ArticleInfographics, InfographicResponse, InfographicType } from '../types';

export const infographicsApi = {
  /**
   * List existing infographics for an article
   */
  list: (articleId: string): Promise<ArticleInfographics> => {
    return get<ArticleInfographics>(`/articles/${articleId}/infographics`);
  },

  /**
   * Generate an infographic for an article
   * Returns cached version if exists, unless forceRegenerate is true
   */
  generate: (
    articleId: string,
    type: InfographicType,
    forceRegenerate: boolean = false
  ): Promise<InfographicResponse> => {
    return post<InfographicResponse>(
      `/articles/${articleId}/infographics/${type}?force_regenerate=${forceRegenerate}`
    );
  },
};
