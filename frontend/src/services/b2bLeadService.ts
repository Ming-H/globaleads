import api from './api';
import type { B2BLead, B2BLeadStatus } from '../types/b2bLead';
import type { PaginatedResponse } from '../types/common';

export interface B2BLeadQuery {
  page: number;
  page_size: number;
  task_id?: number;
  industry?: string;
  region?: string;
  data_source?: string;
  has_email?: boolean;
  status?: B2BLeadStatus;
}

export const b2bLeadService = {
  getLeads: (params: B2BLeadQuery) =>
    api.get<PaginatedResponse<B2BLead>>('/b2b-leads', { params }).then((res) => res.data),

  getLead: (id: number) =>
    api.get<B2BLead>(`/b2b-leads/${id}`).then((res) => res.data),

  updateStatus: (id: number, status: B2BLeadStatus) =>
    api.patch(`/b2b-leads/${id}/status`, { status }).then((res) => res.data),

  exportLeads: (data: {
    task_id?: number;
    format: 'csv' | 'excel';
    filters?: Record<string, unknown>;
  }) =>
    api.post('/b2b-leads/export', data, {
      responseType: 'blob',
    }).then((res) => res),
};
