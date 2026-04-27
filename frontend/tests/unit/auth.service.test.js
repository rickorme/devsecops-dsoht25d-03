// frontend/tests/unit/auth.service.test.js
import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { authService } from '../../src/services/auth.service.js';

// Mock for config
vi.mock('../../src/config', () => ({
  API_BASE_URL: 'http://mocked-for-tests.local'
}));

// THE FIX: Create a complete mock instance
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  };
  
  // Crucial step: Make axios.create() return the exact same instance!
  mockAxiosInstance.create = vi.fn(() => mockAxiosInstance);

  return {
    default: mockAxiosInstance
  };
});

describe('Auth Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // LOGIN TESTS
  // ============================================
  describe('login', () => {
    it('should login successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          user: { username: 'testuser', id: 1 }
        }
      };
      
      axios.post.mockResolvedValue(mockResponse);

      const result = await authService.login({ 
        username: 'testuser', 
        password: 'pass123' 
      });
      
      expect(axios.post).toHaveBeenCalledWith(
        'http://mocked-for-tests.local/auth/login',
        { username: 'testuser', password: 'pass123' },
        { withCredentials: true }
      );
      
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle login error with detail message', async () => {
      const errorResponse = {
        response: {
          data: { detail: 'Invalid credentials' }
        }
      };
      
      axios.post.mockRejectedValue(errorResponse);

      await expect(authService.login({ 
        username: 'wrong', 
        password: 'pass' 
      })).rejects.toThrow('Invalid credentials');
    });

    it('should handle login error with fallback message', async () => {
      const errorResponse = {
        response: {
          data: {}
        }
      };
      
      axios.post.mockRejectedValue(errorResponse);

      await expect(authService.login({ 
        username: 'wrong', 
        password: 'pass' 
      })).rejects.toThrow('Login failed');
    });

    it('should handle network errors', async () => {
      const errorResponse = {
        message: 'Network Error',
        response: undefined
      };
      
      axios.post.mockRejectedValue(errorResponse);

      await expect(authService.login({ 
        username: 'wrong', 
        password: 'pass' 
      })).rejects.toThrow('Login failed');
    });
  });

  // ============================================
  // REGISTER TESTS
  // ============================================
  describe('register', () => {
    it('should register successfully with minimal data', async () => {
      const mockResponse = {
        data: {
          success: true,
          username: 'newuser'
        }
      };
      
      axios.post.mockResolvedValue(mockResponse);

      const result = await authService.register({ 
        username: 'newuser', 
        password: 'pass123',
        email: 'test@example.com'
      });
      
      expect(axios.post).toHaveBeenCalledWith(
        'http://mocked-for-tests.local/auth/register',
        { 
          username: 'newuser', 
          password: 'pass123', 
          full_name: '', 
          email: 'test@example.com' 
        }
      );
      
      expect(result).toEqual(mockResponse.data);
    });

    it('should register with email and full name', async () => {
      const mockResponse = {
        data: {
          success: true,
          username: 'newuser',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      };
      
      axios.post.mockResolvedValue(mockResponse);

      const result = await authService.register({ 
        username: 'newuser', 
        password: 'pass123',
        full_name: 'Test User',
        email: 'test@example.com'
      });
      
      expect(axios.post).toHaveBeenCalledWith(
        'http://mocked-for-tests.local/auth/register',
        { 
          username: 'newuser', 
          password: 'pass123', 
          full_name: 'Test User', 
          email: 'test@example.com' 
        }
      );
      
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle username registration error', async () => {
      const errorResponse = {
        response: {
          data: { detail: 'Username already exists' }
        }
      };
      
      axios.post.mockRejectedValue(errorResponse);

      await expect(authService.register({ 
        username: 'existing', 
        password: 'pass123' 
      })).rejects.toThrow('Username already exists');
    });

    it('should handle email registration error', async () => {
        const errorResponse = {
          response: {
            data: { detail: 'Email already exists' }
          }
        };

        axios.post.mockRejectedValue(errorResponse);

        await expect(authService.register({
          username: 'newuser',
          password: 'pass123',
          email: 'existing@email.com'
        })).rejects.toThrow('Email already exists');
    });
  });

  // ============================================
  // LOGOUT TESTS
  // ============================================
  describe('logout', () => {
    it('should logout successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Logged out successfully'
        }
      };
      
      axios.post.mockResolvedValue(mockResponse);

      const result = await authService.logout();
      
      expect(axios.post).toHaveBeenCalledWith(
        'http://mocked-for-tests.local/auth/logout',
        {},
        { withCredentials: true }
      );
      
      expect(result).toEqual(mockResponse.data);
    });

    it('should return success even if logout fails (graceful degradation)', async () => {
      axios.post.mockRejectedValue(new Error('Network error'));
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const result = await authService.logout();
      
      expect(result).toEqual({ success: true });
      expect(consoleSpy).toHaveBeenCalled();
      
      consoleSpy.mockRestore();
    });
  });

  // ============================================
  // CHECK AUTH TESTS
  // ============================================
  describe('checkAuth', () => {
  it('should return authenticated with user data', async () => {
    const mockUser = {
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      full_name: 'Test User',
      role: 'user',
      is_active: true
    };
    
    // Backend returs user
    const mockResponse = {
      data: mockUser
    };
    
    axios.get.mockResolvedValue(mockResponse);

    const result = await authService.checkAuth();
    
    // Verify endpoint and options
    expect(axios.get).toHaveBeenCalledWith(
      'http://mocked-for-tests.local/auth/me',  
      { withCredentials: true }
    );
    
    // Verify that we return authenticated true with user data
    expect(result).toEqual({
      authenticated: true,
      user: mockUser
    });
  });

  it('should return authenticated true without user data', async () => {

    const mockResponse = {
      data: {}  
    };
    
    axios.get.mockResolvedValue(mockResponse);

    const result = await authService.checkAuth();
    
    expect(result).toEqual({ 
      authenticated: true, 
      user: {} 
    });
  });

  it('should return unauthenticated for 401 status', async () => {
    const errorResponse = {
      response: { status: 401 }
    };
    
    axios.get.mockRejectedValue(errorResponse);

    const result = await authService.checkAuth();
    
    expect(result).toEqual({ authenticated: false, user: null });
  });

  it('should return unauthenticated for 403 status', async () => {
    const errorResponse = {
      response: { status: 403 }
    };
    
    axios.get.mockRejectedValue(errorResponse);

    const result = await authService.checkAuth();
    
    expect(result).toEqual({ authenticated: false, user: null });
  });

  it('should return unauthenticated for network errors', async () => {
    const errorResponse = {
      message: 'Network Error',
      response: undefined
    };
    
    axios.get.mockRejectedValue(errorResponse);
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const result = await authService.checkAuth();
    
    expect(result).toEqual({ authenticated: false, user: null });
    expect(consoleSpy).toHaveBeenCalled();
    
    consoleSpy.mockRestore();
  });
});

  // ============================================
  // PASSWORD RESET TESTS
  // ============================================
  describe('requestPasswordReset', () => {
    it('should request password reset successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Reset email sent'
        }
      };
      
      axios.post.mockResolvedValue(mockResponse);

      const result = await authService.requestPasswordReset({ 
        email: 'test@example.com' 
      });
      
      expect(axios.post).toHaveBeenCalledWith(
        'http://mocked-for-tests.local/auth/reset-password',
        { email: 'test@example.com' }
      );
      
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle request password reset error', async () => {
      const errorResponse = {
        response: {
          data: { detail: 'Email not found' }
        }
      };
      
      axios.post.mockRejectedValue(errorResponse);

      await expect(authService.requestPasswordReset({ 
        email: 'notfound@example.com' 
      })).rejects.toThrow('Email not found');
    });
  });

  describe('resetPassword', () => {
    it('should reset password successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Password reset successful'
        }
      };
      
      axios.post.mockResolvedValue(mockResponse);

      const result = await authService.resetPassword({ 
        token: 'abc123', 
        new_password: 'newPass123' 
      });
      
      expect(axios.post).toHaveBeenCalledWith(
        'http://mocked-for-tests.local/auth/reset-password/confirm',
        { token: 'abc123', new_password: 'newPass123' }
      );
      
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle reset password error', async () => {
      const errorResponse = {
        response: {
          data: { detail: 'Invalid or expired token' }
        }
      };
      
      axios.post.mockRejectedValue(errorResponse);

      await expect(authService.resetPassword({ 
        token: 'invalid', 
        new_password: 'newPass123' 
      })).rejects.toThrow('Invalid or expired token');
    });
  });

  // ============================================
  // EMAIL VERIFICATION TESTS
  // ============================================
  describe('verifyEmail', () => {
    it('should verify email successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Email verified'
        }
      };
      
      axios.post.mockResolvedValue(mockResponse);

      const result = await authService.verifyEmail({ 
        token: 'xyz789' 
      });
      
      expect(axios.post).toHaveBeenCalledWith(
        'http://mocked-for-tests.local/auth/verify-email',
        { token: 'xyz789' }
      );
      
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle verify email error', async () => {
      const errorResponse = {
        response: {
          data: { detail: 'Invalid verification token' }
        }
      };
      
      axios.post.mockRejectedValue(errorResponse);

      await expect(authService.verifyEmail({ 
        token: 'invalid' 
      })).rejects.toThrow('Invalid verification token');
    });
  });

  describe('resendVerificationEmail', () => {
    it('should resend verification email successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          message: 'Verification email resent'
        }
      };
      
      axios.post.mockResolvedValue(mockResponse);

      const result = await authService.resendVerificationEmail({ 
        email: 'test@example.com' 
      });
      
      expect(axios.post).toHaveBeenCalledWith(
        'http://mocked-for-tests.local/auth/resend-verification',
        { email: 'test@example.com' }
      );
      
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle resend verification error', async () => {
      const errorResponse = {
        response: {
          data: { detail: 'Email already verified' }
        }
      };
      
      axios.post.mockRejectedValue(errorResponse);

      await expect(authService.resendVerificationEmail({ 
        email: 'verified@example.com' 
      })).rejects.toThrow('Email already verified');
    });
  });
});