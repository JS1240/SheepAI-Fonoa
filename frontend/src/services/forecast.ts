/**
 * Service for 48-hour threat forecast
 */

import { get } from './api';
import type { ThreatForecast } from '../types';

/**
 * Get 48-hour threat forecast for an article
 */
export async function getThreatForecast(articleId: string): Promise<ThreatForecast> {
  return get<ThreatForecast>(`/forecast/${articleId}`);
}
