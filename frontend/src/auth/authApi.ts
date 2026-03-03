import { apiRequest } from "../lib/api";
import type { LoginResponse, User } from "./types";

export async function login(username: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login-json", "POST", undefined, { username, password });
}

export async function getCurrentUser(accessToken: string): Promise<User> {
  return apiRequest<User>("/auth/me", "GET", accessToken);
}
