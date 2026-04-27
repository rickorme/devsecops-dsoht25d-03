// frontend/src/services/api.js
import axios from 'axios';
import { API_BASE_URL } from '../config/index';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,  // Set the base URL from environment variable
  withCredentials: true, // send cookies with requests for authentication
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging (opțional)
api.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.log(`🚀 ${config.method.toUpperCase()} ${config.url}`, config.data);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling error
api.interceptors.response.use(
  (response) => {
    if (import.meta.env.DEV) {
      console.log('✅ Response:', response.data);
    }
    return response;
  },
  (error) => {
    if (import.meta.env.DEV) {
      console.error('❌ API Error:', error.response?.data || error.message);
    }
    
    // Handle 401 Unauthorized - redirect to login
    if (error.response?.status === 401) {
      const currentPath = window.location.pathname;
      if (!currentPath.includes('/login') && !currentPath.includes('/register')) {
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;