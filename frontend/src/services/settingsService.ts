import api from './api';

export interface AIConfig {
  provider: string;
  model: string;
  api_key?: string;
  base_url?: string;
}

export const settingsService = {
  getAIConfig: () =>
    api.get<AIConfig>('/settings/ai-config').then((res) => res.data),

  updateAIConfig: (data: Partial<AIConfig>) =>
    api.patch<AIConfig>('/settings/ai-config', data).then((res) => res.data),

  getApiUsage: () =>
    api
      .get<Record<string, { used: number; limit: number | string }>>('/settings/api-usage')
      .then((res) => res.data),
};
