/**
 * API Client — Axios-based HTTP client (no authentication).
 */

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// ==========================================
// Upload API
// ==========================================
export const uploadAPI = {
  uploadExcel: (file: File, datasetName?: string, sheetName?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (datasetName) formData.append('dataset_name', datasetName);
    if (sheetName) formData.append('sheet_name', sheetName);
    return api.post('/api/upload/excel', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  listDatasets: () => api.get('/api/upload/datasets'),

  previewDataset: (id: number, limit: number = 20) =>
    api.get(`/api/upload/datasets/${id}/preview?limit=${limit}`),

  deleteDataset: (id: number) => api.delete(`/api/upload/datasets/${id}`),
};

// ==========================================
// Query API
// ==========================================
export const queryAPI = {
  submitQuery: (question: string, datasetTables?: string[]) =>
    api.post('/api/query', { question, dataset_tables: datasetTables }),

  getHistory: (limit: number = 50) =>
    api.get(`/api/query/history?limit=${limit}`),

  getTables: () => api.get('/api/query/tables'),

  getProviders: () => api.get('/api/query/providers'),
};

// ==========================================
// Admin API
// ==========================================
export const adminAPI = {
  getDatasets: () => api.get('/api/admin/datasets'),
  getLogs: (limit: number = 100) => api.get(`/api/admin/logs?limit=${limit}`),
  getStats: () => api.get('/api/admin/stats'),
};

// ==========================================
// Export API
// ==========================================
export const exportAPI = {
  download: (data: {
    columns: string[];
    rows: Record<string, any>[];
    title?: string;
    sql?: string;
    format: string;
  }) => api.post('/api/export/download', data, { responseType: 'blob' }),
};

export default api;
