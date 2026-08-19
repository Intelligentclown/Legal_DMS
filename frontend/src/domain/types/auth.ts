export interface CurrentUser {
  id: string;
  display_name: string;
  roles: string[];
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

