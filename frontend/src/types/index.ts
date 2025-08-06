export interface User {
  username: string;
  status: 'active' | 'disabled';
  quota_bytes: number;
  bytes_used: number;
  usage_percentage?: number;
  auth_types: string[];
}

export interface SystemStatus {
  installed: boolean;
  users_count: number;
  settings: OpenVPNSettings | null;
}

export interface OpenVPNSettings {
  public_ip: string;
  cert_port: number;
  cert_proto: string;
  login_port: number;
  login_proto: string;
  dns: string;
  cipher: string;
}

export interface UserQuotaStatus {
  username: string;
  quota_bytes: number;
  quota_human: string;
  bytes_used: number;
  bytes_used_human: string;
  usage_percentage?: number;
  remaining_bytes?: number;
  remaining_human?: string;
  is_over_quota: boolean;
}

export interface ApiResponse<T = any> {
  message: string;
  error?: string;
  data?: T;
}

export interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped';
  uptime?: string;
}

export interface SystemStats {
  cpu_usage: number;
  ram_usage: number;
  storage_usage: number;
  online_users: number;
  active_users: number;
  total_users: number;
}

export interface TrafficData {
  date: string;
  upload: number;
  download: number;
  total: number;
}

export interface Alert {
  id: string;
  type: 'warning' | 'error' | 'info' | 'success';
  title: string;
  message: string;
  timestamp: Date;
}

export type Theme = 'light' | 'dark';
export type Language = 'en' | 'fa';