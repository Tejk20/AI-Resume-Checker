import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Eye, EyeOff, Mail } from 'lucide-react';
import AuthLayout from '../components/AuthLayout';
import { useAuth } from '../components/AuthContext';
import { api, errorMessage } from '../services/api';

export default function PasswordRecovery({ reset = false }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [token] = useState(() => new URLSearchParams(location.hash.slice(1)).get('token') || '');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  useEffect(() => {
    if (reset && location.hash) navigate('/reset-password', { replace: true });
  }, [reset, location.hash, navigate]);
  async function submit(event) {
    event.preventDefault(); setError('');
    if (reset && password !== confirm) { setError('Passwords do not match.'); return; }
    setBusy(true);
    try {
      const { data } = await api.post(reset ? '/auth/reset-password' : '/auth/forgot-password',
        reset ? { token, password } : { email: email.trim() });
      if (reset) setUser(null);
      setMessage(data.message);
      setPassword(''); setConfirm('');
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <AuthLayout><div className="auth-form-wrap">
    <Link to="/login" className="text-link auth-back">← Back to sign in</Link>
    <span className="eyebrow">ACCOUNT RECOVERY</span>
    <h2>{message ? reset ? 'Password updated.' : 'Check your inbox.' : reset ? 'Choose a new password.' : 'Forgot your password?'}</h2>
    {message ? <div role="status" className="recovery-success"><CheckCircle2 size={32} /><p>{message}</p>
      <Link to={reset ? '/login' : '/forgot-password'} onClick={() => setMessage('')} className="primary full">{reset ? 'Sign in' : 'Try another email'}<ArrowRight size={17} /></Link></div>
      : reset && !token ? <><div role="alert" className="notice danger">Open the reset link from your email, or request a new link.</div><Link to="/forgot-password" className="primary full">Request a new link</Link></>
      : <><p className="muted">{reset ? 'Use a password you have not used elsewhere. You will need to sign in again on your devices.' : 'Enter your account email to request a secure, single-use reset link.'}</p>
      <form onSubmit={submit}>
        {!reset ? <label>Email address<input type="email" autoComplete="email" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} placeholder="you@company.com" /></label>
          : <><label htmlFor="reset-password">New password</label><div className="password-control"><input id="reset-password" type={show ? 'text' : 'password'} autoComplete="new-password" required minLength={10} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} aria-describedby="reset-help" /><button type="button" aria-label={show ? 'Hide password' : 'Show password'} onClick={() => setShow(!show)}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button></div><small id="reset-help" className="muted">At least 10 characters.</small><label>Confirm new password<input type={show ? 'text' : 'password'} autoComplete="new-password" required minLength={10} maxLength={128} value={confirm} onChange={e => setConfirm(e.target.value)} /></label></>}
        {error && <div role="alert" className="notice danger">{error}</div>}
        <button type="submit" disabled={busy} className="primary full">{busy ? 'Please wait…' : reset ? 'Update password' : 'Send reset link'}{!reset ? <Mail size={17} /> : <ArrowRight size={17} />}</button>
      </form></>}
  </div></AuthLayout>;
}
