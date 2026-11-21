import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import Profile from './Profile';
import { api } from '../services/api';
vi.mock('../components/AuthContext', () => ({ useAuth: () => ({ user: { name: 'Test Recruiter', email: 'test@example.test' } }) }));
vi.mock('../services/api', () => ({ api: { post: vi.fn() }, errorMessage: error => error.message }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

function fill(confirm = 'New-test-password-2026') {
  fireEvent.change(screen.getByLabelText('Current password'), { target: { value: 'Emailed-test-password' } });
  fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'New-test-password-2026' } });
  fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: confirm } });
  fireEvent.click(screen.getByRole('button', { name: 'Update password' }));
}

it('changes the password and clears sensitive fields', async () => {
  api.post.mockResolvedValue({ data: { message: 'Password updated.' } });
  render(<Profile />); fill();
  expect(await screen.findByRole('status')).toHaveTextContent('Password updated');
  expect(api.post).toHaveBeenCalledWith('/auth/change-password', { current_password: 'Emailed-test-password', new_password: 'New-test-password-2026' });
  expect(screen.getByLabelText('Current password')).toHaveValue('');
});

it('prevents mismatched confirmation', () => {
  render(<Profile />); fill('Different-password');
  expect(screen.getByRole('alert')).toHaveTextContent('do not match');
  expect(api.post).not.toHaveBeenCalled();
});

it('shows incorrect-current-password errors', async () => {
  api.post.mockRejectedValue(new Error('Your current password is incorrect.'));
  render(<Profile />); fill();
  expect(await screen.findByRole('alert')).toHaveTextContent('current password is incorrect');
});
