import { loadRuntimeSettings } from "./runtimeConfig";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export async function apiRequest<TResponse>(
  path: string,
  method: HttpMethod,
  token?: string,
  body?: unknown,
  extraHeaders?: Record<string, string>
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

  const response = await fetch(url, {
    method,
    headers,
    body: payload,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `${method} ${path} failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}
