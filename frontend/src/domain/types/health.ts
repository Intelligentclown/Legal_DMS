export interface HealthStatus {
  status: string;
  service: string;
  environment: string;
  timestamp: string;
}

export interface AppVersion {
  app_name: string;
  version: string;
  api_prefix: string;
}
