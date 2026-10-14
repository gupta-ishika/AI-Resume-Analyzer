import { API_BASE_URL } from '../config';

class ApiError extends Error {
  constructor(message, status, code, category) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.category = category;
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = { ...options.headers };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, { ...options, headers });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorData = data?.error || {};
    throw new ApiError(
      errorData.message || response.statusText || 'An error occurred',
      response.status,
      errorData.code || 'UNKNOWN_ERROR',
      errorData.category || 'SYSTEM'
    );
  }

  return data;
}

export const apiClient = {
  // Analyses
  async getAnalyses(page = 1, limit = 20) {
    return request(`/analyses?page=${page}&limit=${limit}`);
  },

  async getAnalysis(id) {
    return request(`/analyses/${id}`);
  },

  async createAnalysis({ name, jd_text, jd_file }) {
    const formData = new FormData();
    if (name) formData.append('name', name);
    if (jd_text) formData.append('jd_text', jd_text);
    if (jd_file) formData.append('jd_file', jd_file);

    return request('/analyses', {
      method: 'POST',
      body: formData,
    });
  },

  async deleteAnalysis(id) {
    return request(`/analyses/${id}`, {
      method: 'DELETE',
    });
  },

  // Requirements
  async getRequirements(analysisId) {
    return request(`/analyses/${analysisId}/requirements`);
  },

  async updateRequirements(analysisId, requirements) {
    return request(`/analyses/${analysisId}/requirements`, {
      method: 'PUT',
      body: JSON.stringify(requirements),
    });
  },

  async confirmRequirements(analysisId) {
    return request(`/analyses/${analysisId}/requirements/confirm`, {
      method: 'POST',
    });
  },

  // Resumes
  async uploadResumes(analysisId, fileList) {
    const formData = new FormData();
    for (const file of fileList) {
      formData.append('files', file);
    }
    return request(`/analyses/${analysisId}/resumes`, {
      method: 'POST',
      body: formData,
    });
  },

  async getResumes(analysisId) {
    return request(`/analyses/${analysisId}/resumes`);
  },

  // Execution & Status
  async startAnalysis(analysisId) {
    return request(`/analyses/${analysisId}/start`, {
      method: 'POST',
    });
  },

  async getAnalysisStatus(analysisId) {
    return request(`/analyses/${analysisId}/status`);
  },

  // Candidates & Explanations
  async getCandidates(analysisId) {
    return request(`/analyses/${analysisId}/candidates`);
  },

  async getCandidateDetail(analysisId, candidateId) {
    return request(`/analyses/${analysisId}/candidates/${candidateId}`);
  },

  async requestExplanation(analysisId, candidateId) {
    return request(`/analyses/${analysisId}/candidates/${candidateId}/explanation`, {
      method: 'POST',
    });
  },

  async getExplanation(analysisId, candidateId) {
    return request(`/analyses/${analysisId}/candidates/${candidateId}/explanation`);
  },
};
