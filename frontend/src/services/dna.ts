/**
 * Service for Threat DNA Matching
 */

import { get } from './api';
import type { ThreatDNA } from '../types';

/**
 * Get threat DNA analysis with historical pattern matching
 */
export async function getThreatDNA(articleId: string): Promise<ThreatDNA> {
  return get<ThreatDNA>(`/dna/${articleId}`);
}
