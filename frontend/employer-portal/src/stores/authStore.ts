/**
 * HigherMatch™ Employer Portal - 认证 Store
 * ==========================================
 *
 * Zustand 状态管理 - 用户认证状态
 *
 * 版本: 1.0.0
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ==================== 类型定义 ====================

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'employer' | 'admin' | 'candidate';
  companyName?: string;
  avatar?: string;
}

interface AuthState {
  // 状态
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // 方法
  setUser: (user: User | null) => void;
  setTokens: (accessToken: string, refreshToken?: string) => void;
  logout: () => void;
  checkAuth: () => boolean;
}

// ==================== Store ====================

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // 初始状态
      user: null,
      isAuthenticated: false,
      isLoading: false,

      // 设置用户信息
      setUser: (user) => {
        if (user) {
          localStorage.setItem('user_info', JSON.stringify(user));
          set({ user, isAuthenticated: true });
        } else {
          localStorage.removeItem('user_info');
          set({ user: null, isAuthenticated: false });
        }
      },

      // 设置 Token
      setTokens: (accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken);
        if (refreshToken) {
          localStorage.setItem('refresh_token', refreshToken);
        }
      },

      // 登出
      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_info');
        set({ user: null, isAuthenticated: false });
      },

      // 检查认证状态
      checkAuth: () => {
        const token = localStorage.getItem('access_token');
        const userStr = localStorage.getItem('user_info');

        if (token && userStr) {
          try {
            const user = JSON.parse(userStr) as User;
            set({ user, isAuthenticated: true });
            return true;
          } catch {
            set({ user: null, isAuthenticated: false });
            return false;
          }
        }

        set({ user: null, isAuthenticated: false });
        return false;
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// ==================== 导出 ====================

export default useAuthStore;
