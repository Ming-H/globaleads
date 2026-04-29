import api from './api';
import type { LoginRequest, LoginResponse, RegisterRequest } from '../types/auth';

export const authService = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>('/auth/login', data).then((res) => res.data),

  register: (data: RegisterRequest) =>
    api.post('/auth/register', data).then((res) => res.data),
};
