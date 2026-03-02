// frontend/src/services/auth.service.js
import axios from 'axios';
import { API_BASE_URL } from '../config/index';
  
// Service for handling authentication-related API calls
export const authService = {
  /**
   * Login user with session-based auth
   * Sets HTTP-only cookie automatically
   */
  async login({username, password}) {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, {
        username,
        password
      }, {
        withCredentials: true  // ESSENTIAL for cookies!
      });
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Login failed';
      console.error('Login error:', errorMsg);
      throw new Error(errorMsg);
    }
  },

  /**
   * Register new user
   */
  async register( {username, password, full_name = '', email = ''} ) {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/register`, {
        username,
        password,
        full_name,
        email
      });
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Registration failed';
      console.error('Register error:', errorMsg);
      throw new Error(errorMsg);
    }
  },

  /**
   * Logout user (invalidates session)
   */
  async logout() {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/logout`, {}, {
        withCredentials: true
      });
      return response.data;
    } catch (err) {
      console.warn('Logout error (might be already logged out):', err.message);
      return { success: true }; // Still consider it successful
    }
  },

  //** methods for password reset and email verification **//
  /**
   * Request password reset (forgot password)
   */
  async requestPasswordReset({ email }) {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/reset-password`, {
        email
      });
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to request password reset';
      console.error('Password reset request error:', errorMsg);
      throw new Error(errorMsg);
    }
  },

  /**
   * Reset password with token (from email)
   */
  async resetPassword({ token, new_password }) {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/reset-password/confirm`, {
        token,        // tocken for password reset
        new_password
      });
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to reset password';
      console.error('Password reset error:', errorMsg);
      throw new Error(errorMsg);
    }
  },

  /**
   * Verify email with token
   */
  async verifyEmail({ token }) {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/verify-email`, {
        token        // tocken for email verification
      });
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to verify email';
      console.error('Email verification error:', errorMsg);
      throw new Error(errorMsg);
    }
  },

  /**
   * Resend verification email
   */
  async resendVerificationEmail({ email }) {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/resend-verification`, {
        email
      });
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to resend verification email';
      console.error('Resend verification error:', errorMsg);
      throw new Error(errorMsg);
    }
  },

 /**
   * Check if user is authenticated create a method in backend to check if user is authenticated and return user info if authenticated
   * This is used on app load to determine if user is logged in or not
   * Uses the new /auth/me endpoint
   */
  async checkAuth() {
    try {
      // This will return user info if authenticated, or throw 401 if not
      const response = await axios.get(`${API_BASE_URL}/auth/me`, {
        withCredentials: true  // Important for sending cookies with the request
      });
      
      // response.data contains user info if authenticated, otherwise it would throw 401
      return { 
        authenticated: true, 
        user: response.data 
      };

    } catch (err) {
      // 401 = unauthorized
      if (err.response?.status === 401) {
        return { authenticated: false, user: null };
      }
      
      // other errors (network, etc)
      console.warn('Auth check failed:', err.message);
      return { authenticated: false, user: null };
    }
  }
};  