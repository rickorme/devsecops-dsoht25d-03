// frontend/src/contexts/AuthProvider.jsx
import { useState, useEffect } from 'react';
import AuthContext from './AuthContext';  
import { authService } from '../services/auth.service';

//AuthProvider component to manage authentication state and actions
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null); 
  const [loading, setLoading] = useState(true); 

  useEffect(() => {
    const checkExistingAuth = async () => {
      try {
        const authResult = await authService.checkAuth();
        if (authResult.authenticated && authResult.user) {
          setUser(authResult.user);
        }
      } catch (error) {
        console.warn('No existing auth session:', error);
      } finally {
        setLoading(false);
      }
    };
    checkExistingAuth();
  }, []);

  // Login function that calls the auth service and updates state
  const login = async ({ username, password }) => {
    try {
      const result = await authService.login({ username, password });
      if (result.success && result.user) {
        setUser(result.user);
      }
      return result;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  // Register function that calls the auth service and updates state
  const register = async (userData) => {
    try {
      const result = await authService.register(userData);
      return result;
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  // Logout function that calls the auth service and updates state
  const logout = async () => {
    try {
      await authService.logout();
      setUser(null);
    } catch (error) {
      console.warn('Logout error:', error);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;