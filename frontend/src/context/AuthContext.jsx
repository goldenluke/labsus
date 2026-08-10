import React, { createContext, useContext, useCallback, useEffect, useState } from 'react';
import axios from 'axios';

const AuthContext = createContext({
  hasBphoAccess: false,
  authLoading: true,
  refreshUser: () => {},
});

export function AuthProvider({ children }) {
  const [hasBphoAccess, setHasBphoAccess] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('authToken');
    if (!token) {
      setHasBphoAccess(false);
      setAuthLoading(false);
      return;
    }
    try {
      const response = await axios.get('/api/auth/user/', {
        headers: { Authorization: `Token ${token}` },
      });
      setHasBphoAccess(!!response.data.has_bpho_access);
    } catch (error) {
      setHasBphoAccess(false);
    } finally {
      setAuthLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  return (
    <AuthContext.Provider value={{ hasBphoAccess, authLoading, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
