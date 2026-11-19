import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import Auth from './Auth';
import { api } from '../services/api';
const { setUser } = vi.hoisted(() => ({ setUser: vi.fn() }));
vi.mock('../components/AuthContext', () => ({ useAuth: () => ({ user: null, setUser }) }));
vi.mock('../services/api', () => ({ api: { post: vi.fn() }, errorMessage: () => 'Email or password is incorrect.' }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

function mount(signup = true) {
  render(<MemoryRouter initialEntries={[signup ? '/signup' : '/login']}><Routes>
    <Route path="/signup" element={<Auth signup />} />
    <Route path="/login" element={<Auth />} />
    <Route path="/" element={<p>Your workspace</p>} />
  </Routes></MemoryRouter>);
}
function fill(signup = true) {
  if (signup) fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'Jordan Test' } });
  fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'jordan@example.test' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'A-test-passphrase-42' } });
  if (signup) fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'A-test-passphrase-42' } });
}

it('creates a real account and enters the workspace without storing a token', async () => {
  const user = { id: 'test-user', name: 'Jordan Test' };
  api.post.mockResolvedValue({ data: { user } });
  mount(); fill();
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
  await screen.findByText('Your workspace');
  expect(api.post).toHaveBeenCalledWith('/auth/signup', { name: 'Jordan Test', email: 'jordan@example.test', password: 'A-test-passphrase-42' });
  expect(setUser).toHaveBeenCalledWith(user);
  expect(localStorage.getItem('token')).toBeNull();
});

it('rejects mismatched passwords before sending an account request', async () => {
  mount(); fill();
  fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'A-different-passphrase' } });
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match.');
  expect(api.post).not.toHaveBeenCalled();
});

it('shows login errors and never signs in on a failed request', async () => {
  api.post.mockRejectedValue(new Error('Unauthorized'));
  mount(false); fill(false);
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Email or password is incorrect.');
  await waitFor(() => expect(screen.getByRole('button', { name: 'Sign in' })).not.toBeDisabled());
  expect(setUser).not.toHaveBeenCalled();
});
