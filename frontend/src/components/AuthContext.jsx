import { createContext, useContext, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { api, errorMessage } from '../services/api';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [required, setRequired] = useState(true);
  const [error, setError] = useState('');
  async function refresh() {
    try {
      const { data } = await api.get('/auth/me');
      setUser(data.user); setRequired(data.auth_required); setError('');
    } catch (e) { setError(errorMessage(e)); }
    finally { setReady(true); }
  }
  useEffect(() => { refresh(); }, []);
  async function logout() {
    await api.post('/auth/logout');
    setUser(null);
    localStorage.removeItem('avom-job');
  }
  return <AuthContext.Provider value={{ user, setUser, ready, required, error, refresh, logout }}>
    {children}
  </AuthContext.Provider>;
}

export function RequireAccount({ children }) {
  const { user, ready, required } = useAuth();
  const location = useLocation();
  if (!ready) return <div className="state">Loading your workspace…</div>;
  return required && !user
    ? <Navigate to={'/login?next=' + encodeURIComponent(location.pathname + location.search)} replace />
    : children;
}
