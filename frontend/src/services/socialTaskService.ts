import api from './api';
import type { SocialTask, SocialTaskCreate } from '../types/socialTask';
import type { PaginatedResponse } from '../types/common';

export const socialTaskService = {
  getTasks: (params: {
    page: number;
    page_size: number;
    status?: string;
  }) => api.get<PaginatedResponse<SocialTask>>('/social-tasks', { params }).then((res) => res.data),

  getTask: (id: number) =>
    api.get<SocialTask>(`/social-tasks/${id}`).then((res) => res.data),

  createTask: (data: SocialTaskCreate) =>
    api.post<SocialTask>('/social-tasks', data).then((res) => res.data),

  stopTask: (id: number) =>
    api.post(`/social-tasks/${id}/stop`).then((res) => res.data),

  retryTask: (id: number) =>
    api.post(`/social-tasks/${id}/retry`).then((res) => res.data),
};
