import axios from 'axios';

// 生产环境直接使用 API 域名，开发环境走代理
const API_BASE_URL = import.meta.env.DEV
  ? '/api/v1'
  : (import.meta.env.VITE_API_BASE_URL || 'https://globaleads-api.devfoxai.cn/api/v1');

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default api;
