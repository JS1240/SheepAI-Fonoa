/**
 * Graph API service
 */

import { get } from './api';

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  article_nodes: number;
  entity_nodes: number;
}

export const graphApi = {
  /**
   * Get knowledge graph statistics
   */
  getStats: (): Promise<GraphStats> => {
    return get<GraphStats>('/graph/stats');
  },
};
