export interface SocialTask {
  id: number;
  name: string;
  keywords: string[];
  platforms: string[];
  status: 'pending' | 'running' | 'completed' | 'failed';
  lead_count: number;
  max_results: number;
  min_score: number;
  created_at: string;
  updated_at: string;
}

export interface SocialTaskCreate {
  name: string;
  keywords: string[];
  platforms: string[];
  max_results?: number;
  min_score?: number;
}
