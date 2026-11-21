import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PasswordRecovery from './PasswordRecovery';
import { api } from '../services/api';
const { setUser } = vi.hoisted(() => ({ setUser: vi.fn() }));
vi.mock('../components/AuthContext', () => ({ useAuth: () => ({ setUser }) }));
vi.mock('../services/api', () => ({ api: { post: vi.fn() }, errorMessage: error => error.message }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it('requests a link without showing a password or reset token', async () => {
  api.post.mockResolvedValue({ data: { message: 'If an account matches, a reset link will be sent.' } });
  render(<MemoryRouter><PasswordRecovery /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'test@example.test' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send reset link' }));
  expect(await screen.findByRole('status')).toHaveTextContent('If an account matches');
  expect(api.post).toHaveBeenCalledWith('/auth/forgot-password', { email: 'test@example.test' });
});

it('clearly reports unconfigured delivery instead of claiming success', async () => {
  api.post.mockRejectedValue(new Error('Password-reset email is not configured yet.'));
  render(<MemoryRouter><PasswordRecovery /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'test@example.test' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send reset link' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('not configured');
  expect(screen.queryByRole('heading', { name: 'Check your inbox.' })).not.toBeInTheDocument();
});

it('redeems an email-fragment token and returns the user to sign in', async () => {
  api.post.mockResolvedValue({ data: { message: 'Password updated. Sign in with your new password.' } });
  render(<MemoryRouter initialEntries={['/reset-password#token=synthetic-reset-token-only']}><PasswordRecovery reset /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'New-test-passphrase-2026' } });
  fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'New-test-passphrase-2026' } });
  fireEvent.click(screen.getByRole('button', { name: 'Update password' }));
  expect(await screen.findByRole('status')).toHaveTextContent('Password updated');
  expect(api.post).toHaveBeenCalledWith('/auth/reset-password', { token: 'synthetic-reset-token-only', password: 'New-test-passphrase-2026' });
  expect(setUser).toHaveBeenCalledWith(null);
});

it('explains missing links without allowing an unverified reset', () => {
  render(<MemoryRouter initialEntries={['/reset-password']}><PasswordRecovery reset /></MemoryRouter>);
  expect(screen.getByRole('alert')).toHaveTextContent('Open the reset link');
  expect(screen.queryByRole('button', { name: 'Update password' })).not.toBeInTheDocument();
});
