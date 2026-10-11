/**
 * TicketTriage API Client
 * Dynamically communicates with the Python FastAPI backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      let errorMsg = `HTTP Error ${response.status}`;
      try {
        const errorData = await response.json();
        errorMsg = errorData.detail || errorMsg;
      } catch (e) {
        // Fallback to text
        const text = await response.text();
        if (text) errorMsg = text;
      }
      throw new Error(errorMsg);
    }
    return await response.json();
  } catch (error) {
    console.error(`API Error on ${endpoint}:`, error);
    throw error;
  }
}

export const api = {
  // Health & Config
  getHealth: () => request('/health'),
  getConfig: () => request('/config'),

  // Prediction & Classification
  predict: (payload) => request('/predict', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),

  // Tickets CRUD
  createTicket: (payload) => request('/tickets', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),

  getTickets: (filters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        params.append(key, val);
      }
    });
    const query = params.toString() ? `?${params.toString()}` : '';
    return request(`/tickets${query}`);
  },

  getTicket: (id) => request(`/tickets/${id}`),

  patchTicket: (id, updates) => request(`/tickets/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  }),

  // Analytics & Metrics
  getMetrics: () => request('/metrics'),
};

export default api;
