import React, { useState } from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import UploadResumes from './UploadResumes';
import { api } from '../services/api';
vi.mock('../services/api', () => ({ api: { get: vi.fn(), post: vi.fn() }, errorMessage: e => e.message }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

const sample = { id: 'sample', title: 'Python Developer', is_demo: true, match_status: 'completed' };
const privateJob = { ...sample, id: 'private', is_demo: false, match_status: 'idle' };
function mount(initial = sample) {
  function Controlled() {
    const [jobs, setJobs] = useState([initial]);
    const [selected, setSelected] = useState(initial.id);
    return <UploadResumes {...{ jobs, selected, setSelected }} refreshJobs={async () => { setJobs([privateJob, sample]); return [privateJob, sample]; }} />;
  }
  render(<MemoryRouter><Controlled /></MemoryRouter>);
}
function chooseCV() {
  fireEvent.change(screen.getByLabelText('Resume files'), { target: { files: [new File(['fictional CV'], 'test-candidate.pdf', { type: 'application/pdf' })] } });
}

it('copies a sample job and uploads the selected CV to the private job in one action', async () => {
  let processed = false;
  api.get.mockImplementation(async path => {
    if (path === '/batches/batch') {
      processed = true;
      return { data: { id: 'batch', status: 'completed', total_files: 1, processed_files: 1, failed_files: 0, errors: [] } };
    }
    if (path.endsWith('/candidates')) return { data: { total: path.includes('sample') ? 12 : processed ? 1 : 0 } };
    return { data: path.includes('sample') ? sample : privateJob };
  });
  api.post.mockImplementation(async path => {
    if (path === '/jobs/sample/copy') return { data: privateJob };
    if (path === '/jobs/private/resumes') return { data: { id: 'batch', status: 'pending', total_files: 1, processed_files: 0, failed_files: 0, errors: [] } };
    return { data: { status: 'processing' } };
  });
  mount();
  await screen.findByText(/12 sample candidates/);
  chooseCV();
  expect(screen.getByRole('link', { name: 'View sample rankings' })).toHaveAttribute('href', '/rankings');
  const upload = screen.getByRole('button', { name: 'Upload to my own copy' });
  expect(upload).toBeEnabled();
  fireEvent.click(upload);
  await waitFor(() => expect(api.post).toHaveBeenCalledWith('/jobs/private/resumes', expect.any(FormData), expect.any(Object)));
  const body = api.post.mock.calls.find(([path]) => path === '/jobs/private/resumes')[1];
  expect(body.getAll('files')[0].name).toBe('test-candidate.pdf');
  expect(api.post.mock.calls.some(([path]) => path === '/jobs/sample/resumes')).toBe(false);
  await waitFor(() => expect(screen.getByRole('button', { name: 'Run matching' })).toBeEnabled(), { timeout: 4000 });
  fireEvent.click(screen.getByRole('button', { name: 'Run matching' }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith('/jobs/private/match'));
}, 15000);

it('keeps the selected CV available if making a private copy fails', async () => {
  api.get.mockResolvedValue({ data: { ...sample, total: 12 } });
  api.post.mockRejectedValue(new Error('Could not create your private copy. Please retry.'));
  mount(); chooseCV();
  fireEvent.click(screen.getByRole('button', { name: 'Upload to my own copy' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not create your private copy');
  expect(screen.getByText('test-candidate.pdf')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Upload to my own copy' })).toBeEnabled();
});

it('uploads directly for an existing private job and explains why matching is initially disabled', async () => {
  api.get.mockResolvedValue({ data: { ...privateJob, total: 0 } });
  api.post.mockResolvedValue({ data: { id: 'batch', status: 'completed', total_files: 1, processed_files: 1, failed_files: 0, errors: [] } });
  mount(privateJob);
  expect(screen.getByText('Upload and process a CV first to enable matching.')).toBeInTheDocument();
  chooseCV();
  fireEvent.click(screen.getByRole('button', { name: 'Upload & process resumes' }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith('/jobs/private/resumes', expect.any(FormData), expect.any(Object)));
  expect(api.post.mock.calls.some(([path]) => path.endsWith('/copy'))).toBe(false);
});
