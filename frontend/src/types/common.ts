export interface PaginatedResponse<T> {
  total: number;
  items: T[];
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
}
