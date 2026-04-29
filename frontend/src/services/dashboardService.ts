import api from './api';
import type { DashboardStats, TrendData } from '../types/dashboard';

export const dashboardService = {
  getStats: () =>
    api.get<DashboardStats>('/dashboard/stats').then((res) => res.data),

  getTrends: (params?: { period?: string; days?: number }) =>
    api.get<TrendData>('/dashboard/trends', { params }).then((res) => res.data),
};
