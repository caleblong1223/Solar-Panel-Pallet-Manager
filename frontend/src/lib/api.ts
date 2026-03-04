const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, "") ?? DEFAULT_API_BASE_URL;

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export async function apiRequest<TResponse>(
  path: string,
  method: HttpMethod,
  token?: string,
  body?: unknown
): Promise<TResponse> {
  const url = path.startsWith("http://") || path.startsWith("https://") ? path : `${API_BASE_URL}${path}`;

  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
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
