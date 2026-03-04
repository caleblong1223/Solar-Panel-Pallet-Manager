export type Role = {
  id: number;
  name: string;
  description?: string | null;
};

export type User = {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  roles: Role[];
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
};
