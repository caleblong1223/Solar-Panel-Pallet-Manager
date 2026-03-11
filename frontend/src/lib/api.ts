import { getApiBaseCandidates, loadRuntimeSettings } from "./runtimeConfig";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
const DEFAULT_REQUEST_TIMEOUT_MS = 4000;

export class ApiError extends Error {
  status: number;
  method: HttpMethod;
  path: string;
  errorCode: string | null;

  constructor(message: string, status: number, method: HttpMethod, path: string, errorCode: string | null = null) {
    super(message);
    this.status = status;
    this.method = method;
    this.path = path;
    this.errorCode = errorCode;
  }
}

async function requestRaw(
  url: string,
  method: HttpMethod,
  headers: Record<string, string>,
  payload: BodyInit | undefined,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      method,
      headers,
      body: payload,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(`Request timed out after ${timeoutMs}ms`, 0, method, url);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function shouldTryFallback(error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.status === 0 || error.status >= 500;
  }
  return true;
}

function buildCandidates(path: string): string[] {
  const isAbsolute = path.startsWith("http://") || path.startsWith("https://");
  if (isAbsolute) {
    return [path];
  }
  const configured = getApiBaseCandidates();
  if (configured.length > 0) {
    return configured.map((base) => `${base}${path}`);
  }
  const { apiBaseUrl } = loadRuntimeSettings();
  return [`${apiBaseUrl}${path}`];
}

function buildCandidateEntries(path: string): Array<{ apiBaseUrl: string; url: string }> {
  const isAbsolute = path.startsWith("http://") || path.startsWith("https://");
  if (isAbsolute) {
    const parsed = new URL(path);
    return [{ apiBaseUrl: `${parsed.protocol}//${parsed.host}`, url: path }];
  }
  const configured = getApiBaseCandidates();
  if (configured.length > 0) {
    return configured.map((base) => ({ apiBaseUrl: base, url: `${base}${path}` }));
  }
  const { apiBaseUrl } = loadRuntimeSettings();
  return [{ apiBaseUrl, url: `${apiBaseUrl}${path}` }];
}

export type ApiResponseWithSource<TResponse> = {
  data: TResponse;
  apiBaseUrl: string;
};

export async function apiRequestAcrossCandidatesWithSource<TResponse>(
  path: string,
  method: HttpMethod,
  token?: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
  timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
  continueOnStatuses: number[] = []
): Promise<ApiResponseWithSource<TResponse>> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (extraHeaders) {
    Object.assign(headers, extraHeaders);
  }

  let payload: BodyInit | undefined;
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const candidates = buildCandidateEntries(path);
  let response: Response | null = null;
  let responseApiBaseUrl: string | null = null;
  let lastError: unknown = null;
  for (let i = 0; i < candidates.length; i += 1) {
    const candidate = candidates[i];
    try {
      response = await requestRaw(candidate.url, method, headers, payload, timeoutMs);
      responseApiBaseUrl = candidate.apiBaseUrl;
      if (!response.ok) {
        if (continueOnStatuses.includes(response.status) && i < candidates.length - 1) {
          lastError = new ApiError(`${method} ${path} failed with status ${response.status}`, response.status, method, path);
          response = null;
          responseApiBaseUrl = null;
          continue;
        }
        if (response.status >= 500 && i < candidates.length - 1) {
          lastError = new ApiError(`${method} ${path} failed with status ${response.status}`, response.status, method, path);
          response = null;
          responseApiBaseUrl = null;
          continue;
        }
      }
      break;
    } catch (error) {
      lastError = error;
      if (i < candidates.length - 1 && shouldTryFallback(error)) {
        continue;
      }
      throw error;
    }
  }
  if (!response || !responseApiBaseUrl) {
    throw (lastError instanceof Error ? lastError : new Error("Request failed"));
  }

  if (!response.ok) {
    const text = await response.text();
    let message = text || `${method} ${path} failed with status ${response.status}`;
    let errorCode: string | null = null;
    try {
      const parsed = JSON.parse(text) as { detail?: string | { error_code?: string; message?: string } };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
      } else if (parsed.detail && typeof parsed.detail === "object") {
        if (typeof parsed.detail.message === "string") {
          message = parsed.detail.message;
        }
        if (typeof parsed.detail.error_code === "string") {
          errorCode = parsed.detail.error_code;
        }
      }
    } catch {
      // Non-JSON error body.
    }
    throw new ApiError(message, response.status, method, path, errorCode);
  }

  if (response.status === 204) {
    return { data: undefined as TResponse, apiBaseUrl: responseApiBaseUrl };
  }

  return {
    data: (await response.json()) as TResponse,
    apiBaseUrl: responseApiBaseUrl,
  };
}

export async function apiRequestAcrossCandidates<TResponse>(
  path: string,
  method: HttpMethod,
  token?: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
  timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
  continueOnStatuses: number[] = []
): Promise<TResponse> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (extraHeaders) {
    Object.assign(headers, extraHeaders);
  }

  let payload: BodyInit | undefined;
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const candidates = buildCandidates(path);
  let response: Response | null = null;
  let lastError: unknown = null;
  for (let i = 0; i < candidates.length; i += 1) {
    const url = candidates[i];
    try {
      response = await requestRaw(url, method, headers, payload, timeoutMs);
      if (!response.ok) {
        if (continueOnStatuses.includes(response.status) && i < candidates.length - 1) {
          lastError = new ApiError(`${method} ${path} failed with status ${response.status}`, response.status, method, path);
          response = null;
          continue;
        }
        if (response.status >= 500 && i < candidates.length - 1) {
          lastError = new ApiError(`${method} ${path} failed with status ${response.status}`, response.status, method, path);
          response = null;
          continue;
        }
      }
      break;
    } catch (error) {
      lastError = error;
      if (i < candidates.length - 1 && shouldTryFallback(error)) {
        continue;
      }
      throw error;
    }
  }
  if (!response) {
    throw (lastError instanceof Error ? lastError : new Error("Request failed"));
  }

  if (!response.ok) {
    const text = await response.text();
    let message = text || `${method} ${path} failed with status ${response.status}`;
    let errorCode: string | null = null;
    try {
      const parsed = JSON.parse(text) as { detail?: string | { error_code?: string; message?: string } };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
      } else if (parsed.detail && typeof parsed.detail === "object") {
        if (typeof parsed.detail.message === "string") {
          message = parsed.detail.message;
        }
        if (typeof parsed.detail.error_code === "string") {
          errorCode = parsed.detail.error_code;
        }
      }
    } catch {
      // Non-JSON error body.
    }
    throw new ApiError(message, response.status, method, path, errorCode);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

export async function apiRequest<TResponse>(
  path: string,
  method: HttpMethod,
  token?: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
  timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS
): Promise<TResponse> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (extraHeaders) {
    Object.assign(headers, extraHeaders);
  }

  let payload: BodyInit | undefined;
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const candidates = buildCandidates(path);

  let response: Response | null = null;
  let lastError: unknown = null;
  for (let i = 0; i < candidates.length; i += 1) {
    const url = candidates[i];
    try {
      response = await requestRaw(url, method, headers, payload, timeoutMs);
      if (!response.ok && response.status >= 500 && i < candidates.length - 1) {
        lastError = new ApiError(`${method} ${path} failed with status ${response.status}`, response.status, method, path);
        continue;
      }
      break;
    } catch (error) {
      lastError = error;
      if (i < candidates.length - 1 && shouldTryFallback(error)) {
        continue;
      }
      throw error;
    }
  }
  if (!response) {
    throw (lastError instanceof Error ? lastError : new Error("Request failed"));
  }

  if (!response.ok) {
    const text = await response.text();
    let message = text || `${method} ${path} failed with status ${response.status}`;
    let errorCode: string | null = null;
    try {
      const parsed = JSON.parse(text) as { detail?: string | { error_code?: string; message?: string } };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
      } else if (parsed.detail && typeof parsed.detail === "object") {
        if (typeof parsed.detail.message === "string") {
          message = parsed.detail.message;
        }
        if (typeof parsed.detail.error_code === "string") {
          errorCode = parsed.detail.error_code;
        }
      }
    } catch {
      // Non-JSON error body.
    }
    throw new ApiError(message, response.status, method, path, errorCode);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}
