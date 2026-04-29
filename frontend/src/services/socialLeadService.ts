import api from './api';
import type { SocialLead, SocialLeadStatus } from '../types/socialLead';
import type { PaginatedResponse } from '../types/common';

export interface SocialLeadQuery {
  page: number;
  page_size: number;
  task_id?: number;
  platform?: string;
  min_score?: number;
  tag?: string;
  status?: SocialLeadStatus;
  sort_by?: string;
  sort_order?: string;
}

export const socialLeadService = {
  getLeads: (params: SocialLeadQuery) =>
    api.get<PaginatedResponse<SocialLead>>('/social-leads', { params }).then((res) => res.data),

  getLead: (id: number) =>
    api.get<SocialLead>(`/social-leads/${id}`).then((res) => res.data),

  updateStatus: (id: number, status: SocialLeadStatus) =>
    api.patch(`/social-leads/${id}/status`, { status }).then((res) => res.data),

  exportLeads: (data: {
    task_id?: number;
    format: 'csv' | 'excel';
    filters?: Record<string, unknown>;
  }) =>
    api.post('/social-leads/export', data, {
      responseType: 'blob',
    }).then((res) => res),
};
