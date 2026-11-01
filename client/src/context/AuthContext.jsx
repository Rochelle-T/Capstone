import React, { createContext, useState, useEffect } from 'react';
import { authService } from '../services/api';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check if user is already logged in
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const storedUser = localStorage.getItem('user');
    
    if (token && storedUser) {
      authService.getCurrentUser()
        .then((userInfo) => {
          localStorage.setItem('user', JSON.stringify(userInfo));
          setUser(userInfo);
        })
        .catch(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          setUser(null);
        })
        .finally(() => setLoading(false));
      return;
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const handleAuthExpired = () => {
      setUser(null);
      setError('Your session expired. Please sign in again.');
    };
    window.addEventListener('auth-expired', handleAuthExpired);
    return () => window.removeEventListener('auth-expired', handleAuthExpired);
  }, []);

  const register = async (email, password, username) => {
    try {
      setError(null);
      const response = await authService.register(email, password, username);
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('user', JSON.stringify({
        user_id: response.user_id,
        email,
        username: username || email.split('@')[0],
      }));
      setUser(response);
      return response;
    } catch (err) {
      const message = err.response?.data?.detail || 'Registration failed';
      setError(message);
      throw new Error(message);
    }
  };

  const setAuthenticatedUser = async (response) => {
    localStorage.setItem('access_token', response.access_token);
    const userInfo = await authService.getCurrentUser();
    localStorage.setItem('user', JSON.stringify(userInfo));
    setUser(userInfo);
    return response;
  };

  const login = async (email, password) => {
    try {
      setError(null);
      const response = await authService.login(email, password);
      return await setAuthenticatedUser(response);
    } catch (err) {
      const message = err.response?.data?.detail || 'Login failed';
      setError(message);
      throw new Error(message);
    }
  };

  const loginAsDemo = async () => {
    const demoEmail = 'demo@astrosense.example.com';
    const demoPassword = 'AstroSenseDemo123!';

    try {
      setError(null);
      let response;

      try {
        response = await authService.login(demoEmail, demoPassword);
      } catch (err) {
        if (err.response?.status !== 401) {
          throw err;
        }
        response = await authService.register(demoEmail, demoPassword, 'Demo User');
      }

      return await setAuthenticatedUser(response);
    } catch (err) {
      const message = err.response?.data?.detail || 'Demo login failed';
      setError(message);
      throw new Error(message);
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
    setError(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, error, register, login, loginAsDemo, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
