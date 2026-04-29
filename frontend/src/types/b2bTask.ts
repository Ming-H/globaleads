export interface B2BTask {
  id: number;
  name: string;
  industry: string;
  region: string;
  company_size: string;
  data_sources: string[];
  status: 'pending' | 'running' | 'completed' | 'failed';
  lead_count: number;
  max_results: number;
  created_at: string;
  updated_at: string;
}

export interface B2BTaskCreate {
  name: string;
  industry: string;
  region: string;
  company_size?: string;
  data_sources: string[];
  max_results?: number;
}
