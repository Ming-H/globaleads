export type SocialLeadStatus = 'uncontacted' | 'contacted' | 'replied' | 'invalid';

export interface SocialLead {
  id: number;
  task_id: number;
  platform: string;
  author_name: string;
  author_url: string;
  content: string;
  post_url: string;
  published_at: string;
  ai_score: number;
  ai_tags: string[];
  ai_analysis: string;
  status: SocialLeadStatus;
  created_at: string;
}
