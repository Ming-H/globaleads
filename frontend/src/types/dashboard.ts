export interface DashboardStats {
  social_leads: {
    total: number;
    this_week: number;
    by_platform: Record<string, number>;
    avg_score: number;
    by_tag: Record<string, number>;
  };
  b2b_leads: {
    total: number;
    this_week: number;
    by_source: Record<string, number>;
    with_email: number;
    by_industry: Record<string, number>;
  };
  tasks: {
    social_total: number;
    b2b_total: number;
    success_rate: number;
  };
  api_usage: Record<
    string,
    {
      used: number;
      limit: number | string;
    }
  >;
}

export interface TrendData {
  dates: string[];
  social_leads: number[];
  b2b_leads: number[];
}
