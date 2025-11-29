/**
 * Base API client for Security Intelligence Platform
 */

const API_BASE_URL = '/api';

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message?: string
  ) {
    super(message || `API Error: ${status} ${statusText}`);
    this.name = 'ApiError';
  }
}

export interface FetchOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

/**
 * Build URL with query parameters
 */
function buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined>): string {
  const url = new URL(`${API_BASE_URL}${endpoint}`, window.location.origin);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
}

/**
 * Generic fetch wrapper with error handling
 */
export async function fetchApi<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { params, ...fetchOptions } = options;

  const url = buildUrl(endpoint, params);

  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      ...defaultHeaders,
      ...fetchOptions.headers,
    },
  });

  if (!response.ok) {
    let errorMessage: string | undefined;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message;
    } catch {
      // Response is not JSON
    }
    throw new ApiError(response.status, response.statusText, errorMessage);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return {} as T;
  }

  return JSON.parse(text) as T;
}

/**
 * GET request helper
 */
export async function get<T>(
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined>
): Promise<T> {
  return fetchApi<T>(endpoint, { method: 'GET', params });
}

/**
 * POST request helper
 */
export async function post<T, D = unknown>(
  endpoint: string,
  data?: D
): Promise<T> {
  return fetchApi<T>(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
}
