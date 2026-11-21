import { useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, Eye, EyeOff } from 'lucide-react';
import { api, errorMessage } from '../services/api';
import { useAuth } from '../components/AuthContext';
import AuthLayout from '../components/AuthLayout';

export default function Auth({ signup = false }) {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [values, setValues] = useState({ name: '', email: '', password: '', confirm: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [show, setShow] = useState(false);
  const requested = params.get('next') || '/';
  const next = requested.startsWith('/') && !requested.startsWith('//') && !requested.startsWith('/login') && !requested.startsWith('/signup') ? requested : '/';
  if (user) return <Navigate to={next} replace />;
  async function submit(event) {
    event.preventDefault(); setError('');
    if (signup && values.password !== values.confirm) {
      setError('Passwords do not match.'); return;
    }
    setBusy(true);
    try {
      const payload = { email: values.email.trim(), password: values.password };
      if (signup) payload.name = values.name.trim();
      const { data } = await api.post(signup ? '/auth/signup' : '/auth/login', payload);
      setUser(data.user);
      localStorage.removeItem('avom-job');
      navigate(next, { replace: true });
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  const update = key => event => setValues({ ...values, [key]: event.target.value });
  return <AuthLayout>
      <div className="auth-form-wrap">
        <Link to="/" className="text-link auth-back">← Explore the sample workspace</Link>
        <span className="eyebrow">YOUR RECRUITER WORKSPACE</span>
        <h2>{signup ? 'Make room for your next hire.' : 'Welcome back.'}</h2>
        <p className="muted">{signup ? 'Create an account to manage your jobs and evaluate candidates.' : 'Sign in to pick up where you left off.'}</p>
        <form onSubmit={submit}>
          {signup && <label>Full name<input autoComplete="name" required minLength={2} maxLength={100} value={values.name} onChange={update('name')} placeholder="Your full name" /></label>}
          <label>Email address<input type="email" autoComplete="email" required maxLength={254} value={values.email} onChange={update('email')} placeholder="you@company.com" /></label>
          <label htmlFor="account-password">Password</label>
          <div className="password-control"><input id="account-password" type={show ? 'text' : 'password'} autoComplete={signup ? 'new-password' : 'current-password'} required minLength={10} maxLength={128} value={values.password} onChange={update('password')} aria-describedby={signup ? 'password-help' : undefined} /><button type="button" aria-label={show ? 'Hide password' : 'Show password'} onClick={() => setShow(!show)}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>
          {signup && <><small id="password-help" className="muted">Use at least 10 characters.</small><label>Confirm password<input type={show ? 'text' : 'password'} autoComplete="new-password" required minLength={10} maxLength={128} value={values.confirm} onChange={update('confirm')} /></label></>}
          {error && <div role="alert" className="notice danger">{error}</div>}
          <button disabled={busy} className="primary full" type="submit">{busy ? 'Please wait…' : signup ? 'Create account' : 'Sign in'}<ArrowRight size={17} /></button>
        </form>
        <p className="auth-switch"><Link className="text-link" to="/forgot-password">Forgot password?</Link></p>
        <p className="auth-switch">{signup ? 'Already have an account?' : 'New to HireLens AI?'}{' '}<Link className="text-link" to={(signup ? '/login' : '/signup') + '?next=' + encodeURIComponent(next)}>{signup ? 'Sign in' : 'Create an account'}</Link></p>
        <p className="muted small">Explore fictional candidates in the sample workspace, then start your own search.</p>
      </div>
  </AuthLayout>;
}
