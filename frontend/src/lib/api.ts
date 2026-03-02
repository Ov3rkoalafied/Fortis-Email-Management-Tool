import axios from 'axios'
import type { AuthStatus, ApplyResult, ProjectEmailData, UndoOperation, EmailTableRow } from '../types'

const api = axios.create({ baseURL: 'http://localhost:8000' })

export const auth = {
  status: () => api.get<AuthStatus>('/api/auth/status').then(r => r.data),
  login: () => api.post<AuthStatus>('/api/auth/login').then(r => r.data),
  logout: () => api.post('/api/auth/logout').then(r => r.data),
}

export const emails = {
  load: (project_numbers: string[], email_limit: number, time_window_minutes: number) =>
    api.post<ProjectEmailData[]>('/api/emails/load', {
      project_numbers, email_limit, time_window_minutes,
    }).then(r => r.data),
}

export const apply = {
  duplicates: (project_number: string, rows: EmailTableRow[]) =>
    api.post<ApplyResult>('/api/apply/duplicates', { project_number, rows }).then(r => r.data),
  numbering: (project_number: string, rows: EmailTableRow[]) =>
    api.post<ApplyResult>('/api/apply/numbering', { project_number, rows }).then(r => r.data),
}

export const undo = {
  history: () => api.get<UndoOperation[]>('/api/undo/history').then(r => r.data),
  revert: (operation_id: string) =>
    api.post<ApplyResult>(`/api/undo/${operation_id}`).then(r => r.data),
}

export const testConnection = () =>
  api.get('/api/test/connection').then(r => r.data)
