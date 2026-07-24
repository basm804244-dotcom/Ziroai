import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      timeout: 30000,
      headers: { 'Content-Type': 'application/json' },
    });

    this.client.interceptors.request.use(
      (config) => {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
        if (token) config.headers.Authorization = `Bearer ${token}`;
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token');
          if (typeof window !== 'undefined') window.location.href = '/auth/login';
        }
        return Promise.reject(error);
      }
    );
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return (await this.client.get<T>(url, config)).data;
  }
  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return (await this.client.post<T>(url, data, config)).data;
  }
  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return (await this.client.patch<T>(url, data, config)).data;
  }
  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return (await this.client.delete<T>(url, config)).data;
  }
}

export const api = new ApiClient();
export default api;
