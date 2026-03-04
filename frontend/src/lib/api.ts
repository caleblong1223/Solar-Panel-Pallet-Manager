import { loadRuntimeSettings } from "./runtimeConfig";

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

export async function apiRequest<TResponse>(
  path: string,
  method: HttpMethod,
  token?: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
  timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS
): Promise<TResponse> {
  const { apiBaseUrl } = loadRuntimeSettings();
  const url = path.startsWith("http://") || path.startsWith("https://") ? path : `${apiBaseUrl}${path}`;

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

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: payload,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(`Request timed out after ${timeoutMs}ms`, 0, method, path);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
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
