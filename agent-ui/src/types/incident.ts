export interface Incident {
  id: string;
  status: 'INVESTIGATING' | 'COMPLETED' | 'FAILED' | 'RESOLVED';
  created_at: number;
  updated_at: number;
  alertname: string;
  service: string;
  starts_at?: string;
  summary?: string;
  description?: string;
  query: string;
  response?: string;
  error?: string;
}
