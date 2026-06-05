import axios from 'axios';

// Connect to the backend API. 
// When running in dev mode, this hits the local FastAPI server.
// In production, this can be configured via environment variables.
export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BACKEND_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export const getAnalytics = async () => {
  const response = await api.get('/analytics');
  return response.data;
};

export const getDocuments = async () => {
  const response = await api.get('/documents');
  return response.data;
};

export const searchCandidates = async (query: string, topK: number = 5) => {
  const response = await api.get('/search', { params: { query, top_k: topK } });
  return response.data;
};

export const uploadDocuments = async (files: FileList, type: string) => {
  const promises = Array.from(files).map((file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload', formData, {
      params: type !== 'auto-detect' ? { document_type: type } : {},
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  });
  return Promise.all(promises);
};

export default api;
