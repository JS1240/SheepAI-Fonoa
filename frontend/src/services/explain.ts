/**
 * Service for audience-specific threat explanations
 */

import { post } from './api';
import type { ExplainToRequest, ExplainToResponse } from '../types';

/**
 * Translate threat content for a specific audience (CEO, Board, Developers)
 */
export async function explainToAudience(
  request: ExplainToRequest
): Promise<ExplainToResponse> {
  return post<ExplainToResponse, ExplainToRequest>('/explain-to', request);
}
