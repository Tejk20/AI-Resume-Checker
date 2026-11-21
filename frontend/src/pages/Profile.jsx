import { useState } from 'react';
import { useAuth } from '../components/AuthContext';
import { api, errorMessage } from '../services/api';

export default function Profile() {
  const { user } = useAuth();
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  async function submit(event) {
    event.preventDefault(); setError(''); setMessage('');
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    setBusy(true);
    try {
      const { data } = await api.post('/auth/change-password', { current_password: current, new_password: password });
      setMessage(data.message); setCurrent(''); setPassword(''); setConfirm('');
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <section className="profile-settings">
    <span className="eyebrow">YOUR ACCOUNT</span><h1>Profile settings</h1>
    <p className="muted">Manage your account and password.</p>
    <div className="card profile-settings-card"><h2>Account details</h2><p>{user?.name}</p><p className="muted">{user?.email}</p></div>
    <div className="card profile-settings-card"><h2>Update password</h2>
      <p className="muted">You can keep using the password you signed in with, including an emailed temporary password, or choose a new one here.</p>
      <form onSubmit={submit}>
        <label>Current password<input type="password" autoComplete="current-password" required minLength={10} maxLength={128} value={current} onChange={e => setCurrent(e.target.value)} /></label>
        <label>New password<input type="password" autoComplete="new-password" required minLength={10} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} aria-describedby="profile-password-help" /></label>
        <small id="profile-password-help" className="muted">Use 10–128 characters. Updating signs out your other devices.</small>
        <label>Confirm new password<input type="password" autoComplete="new-password" required minLength={10} maxLength={128} value={confirm} onChange={e => setConfirm(e.target.value)} /></label>
        {error && <div role="alert" className="notice danger">{error}</div>}
        {message && <div role="status" className="notice">{message}</div>}
        <button className="primary" type="submit" disabled={busy}>{busy ? 'Updating…' : 'Update password'}</button>
      </form>
    </div>
  </section>;
}
