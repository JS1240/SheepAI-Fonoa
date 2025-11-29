/**
 * Articles API service
 */

import { get } from './api';
import type { Article, ArticleSummary, GraphVisualization, StoryTimeline } from '../types';

export interface ArticleListParams {
  q?: string;
  category?: string;
  days?: number;
  limit?: number;
}

export const articlesApi = {
  /**
   * List articles with optional filters
   */
  list: (params: ArticleListParams = {}): Promise<ArticleSummary[]> => {
    return get<ArticleSummary[]>('/articles', {
      q: params.q,
      category: params.category,
      days: params.days ?? 7,
      limit: params.limit ?? 20,
    });
  },

  /**
   * Get a single article by ID
   */
  getById: (id: string): Promise<Article> => {
    return get<Article>(`/articles/${id}`);
  },

  /**
   * Get knowledge graph connections for an article
   */
  getConnections: (id: string, depth: number = 2): Promise<GraphVisualization> => {
    return get<GraphVisualization>(`/articles/${id}/connections`, { depth });
  },

  /**
   * Get story timeline for an article
   */
  getTimeline: (id: string): Promise<StoryTimeline> => {
    return get<StoryTimeline>(`/articles/${id}/timeline`);
  },
};
