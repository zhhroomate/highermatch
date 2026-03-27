/**
 * HigherMatch™ Employer Portal - API Client
 * ==========================================
 *
 * Axios 封装，包含：
 * 1. 请求拦截器：自动附加 JWT token
 * 2. 响应拦截器：401 自动刷新 token 并重试
 * 3. 统一的错误处理
 *
 * 版本: 1.0.0
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';

// ==================== 常量配置 ====================

// API 基础路径配置
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' ? window.location.origin : '');
const API_TIMEOUT = 30000; // 30秒超时

// Token 键名
const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

// ==================== API Client 类 ====================

class ApiClient {
  private client: AxiosInstance;
  private isRefreshing: boolean = false;
  private refreshSubscribers: ((token: string) => void)[] = [];

  constructor() {
    // 创建 axios 实例
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: API_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 初始化拦截器
    this.setupInterceptors();
  }

  /**
   * 设置请求和响应拦截器
   */
  private setupInterceptors(): void {
    // ==================== 请求拦截器 ====================
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // 从 localStorage 获取 token
        const token = localStorage.getItem(TOKEN_KEY);

        // 如果有 token，附加到请求头
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // 添加请求时间戳（用于调试）
        config.headers['X-Request-Time'] = new Date().toISOString();

        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error: AxiosError) => {
        console.error('[API] Request Error:', error);
        return Promise.reject(error);
      }
    );

    // ==================== 响应拦截器 ====================
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        console.log(`[API] Response ${response.status}:`, response.config.url);
        return response;
      },
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        // 处理 401 未授权
        if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
          if (this.isRefreshing) {
            // 正在刷新，等待刷新完成
            return new Promise((resolve) => {
              this.refreshSubscribers.push((token: string) => {
                if (originalRequest.headers) {
                  originalRequest.headers.Authorization = `Bearer ${token}`;
                }
                resolve(this.client(originalRequest));
              });
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            // 尝试刷新 token
            const newToken = await this.refreshToken();

            if (newToken) {
              // 通知所有等待的请求
              this.refreshSubscribers.forEach((callback) => callback(newToken));
              this.refreshSubscribers = [];

              // 重试原始请求
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${newToken}`;
              }
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            // 刷新失败，清除 token 并跳转登录
            this.clearTokens();
            window.location.href = '/employer/login';
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        // 处理其他错误
        return this.handleError(error);
      }
    );
  }

  /**
   * 刷新 Access Token
   */
  private async refreshToken(): Promise<string | null> {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

    if (!refreshToken) {
      return null;
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });

      const { access_token, refresh_token } = response.data;

      // 保存新 token
      localStorage.setItem(TOKEN_KEY, access_token);
      if (refresh_token) {
        localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
      }

      console.log('[API] Token refreshed successfully');
      return access_token;
    } catch (error) {
      console.error('[API] Token refresh failed:', error);
      return null;
    }
  }

  /**
   * 处理错误响应
   */
  private handleError(error: AxiosError): Promise<never> {
    if (error.response) {
      // 服务器返回错误
      const status = error.response.status;
      const data = error.response.data as any;

      switch (status) {
        case 400:
          console.error('[API] Bad Request:', data?.message || '请求参数错误');
          break;
        case 403:
          console.error('[API] Forbidden:', data?.message || '没有权限访问');
          break;
        case 404:
          console.error('[API] Not Found:', data?.message || '资源不存在');
          break;
        case 500:
          console.error('[API] Server Error:', data?.message || '服务器错误');
          break;
        default:
          console.error('[API] Error:', data?.message || '未知错误');
      }
    } else if (error.request) {
      // 请求发出但没有收到响应
      console.error('[API] Network Error: No response received');
    } else {
      // 请求配置出错
      console.error('[API] Request Error:', error.message);
    }

    return Promise.reject(error);
  }

  /**
   * 清除所有 token
   */
  private clearTokens(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    this.refreshSubscribers = [];
  }

  /**
   * 设置 Token
   */
  public setTokens(accessToken: string, refreshToken?: string): void {
    localStorage.setItem(TOKEN_KEY, accessToken);
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
  }

  /**
   * 获取 Token
   */
  public getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  /**
   * 清除 Token
   */
  public clearTokensPublic(): void {
    this.clearTokens();
  }

  // ==================== HTTP 方法 ====================

  /**
   * GET 请求
   */
  async get<T = any>(url: string, params?: object, config?: object): Promise<T> {
    const response = await this.client.get<T>(url, { params, ...config });
    return response.data;
  }

  /**
   * POST 请求
   */
  async post<T = any>(url: string, data?: object, config?: object): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  /**
   * PUT 请求
   */
  async put<T = any>(url: string, data?: object, config?: object): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  /**
   * PATCH 请求
   */
  async patch<T = any>(url: string, data?: object, config?: object): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  /**
   * DELETE 请求
   */
  async delete<T = any>(url: string, config?: object): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }
}

// ==================== 导出单例 ====================

export const apiClient = new ApiClient();

// ==================== 导出类型 ====================

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: {
    items: T[];
    total: number;
    page: number;
    page_size: number;
  };
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

export default apiClient;
