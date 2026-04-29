import api from './api';
import type { B2BTask, B2BTaskCreate } from '../types/b2bTask';
import type { PaginatedResponse } from '../types/common';

export const b2bTaskService = {
  getTasks: (params: {
    page: number;
    page_size: number;
    status?: string;
  }) => api.get<PaginatedResponse<B2BTask>>('/b2b-tasks', { params }).then((res) => res.data),

  getTask: (id: number) =>
    api.get<B2BTask>(`/b2b-tasks/${id}`).then((res) => res.data),

  createTask: (data: B2BTaskCreate) =>
    api.post<B2BTask>('/b2b-tasks', data).then((res) => res.data),

  stopTask: (id: number) =>
    api.post(`/b2b-tasks/${id}/stop`).then((res) => res.data),

  retryTask: (id: number) =>
    api.post(`/b2b-tasks/${id}/retry`).then((res) => res.data),
};
