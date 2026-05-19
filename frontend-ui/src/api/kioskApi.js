import { LOCAL_SERVICE_CATEGORIES } from '../data/options';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API 요청 실패: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export async function startSession(userType = 'NORMAL') {
  try {
    return await request('/api/session/start', {
      method: 'POST',
      body: JSON.stringify({ userType }),
    });
  } catch (error) {
    return {
      sessionId: `local-session-${Date.now()}`,
      accessibility: {
        largeFont: false,
        highContrast: false,
        simpleMode: false,
        lowScreenMode: false,
        fontSize: '16px',
      },
      mock: true,
    };
  }
}

export async function endSession(sessionId) {
  if (!sessionId) return null;
  try {
    return await request('/api/session/end', {
      method: 'POST',
      body: JSON.stringify({ sessionId }),
    });
  } catch {
    return null;
  }
}

export async function updateAccessibility(sessionId, accessibility) {
  if (!sessionId) return accessibility;
  try {
    return await request(`/api/session/${sessionId}/accessibility`, {
      method: 'PUT',
      body: JSON.stringify(accessibility),
    });
  } catch {
    return accessibility;
  }
}

export async function saveInteractionLog(sessionId, action, payload = {}) {
  if (!sessionId) return null;
  try {
    return await request('/api/session/log', {
      method: 'POST',
      body: JSON.stringify({ sessionId, action, payload, createdAt: new Date().toISOString() }),
    });
  } catch {
    return null;
  }
}

export async function getServices() {
  try {
    return await request('/api/services');
  } catch {
    return LOCAL_SERVICE_CATEGORIES;
  }
}

export async function getServicesByCategory(categoryId) {
  try {
    return await request(`/api/services/category/${categoryId}`);
  } catch {
    return LOCAL_SERVICE_CATEGORIES.find((category) => category.id === categoryId) || null;
  }
}

export async function createApplication(applicationPayload) {
  try {
    return await request('/api/applications', {
      method: 'POST',
      body: JSON.stringify(applicationPayload),
    });
  } catch {
    return {
      applicationNo: `APP-${Date.now()}`,
      ...applicationPayload,
      status: 'RECEIVED',
      mock: true,
    };
  }
}

export async function getApplicationStatus(applicationNo) {
  return request(`/api/applications/${applicationNo}`);
}

export async function getApplicationsBySession(sessionId) {
  return request(`/api/applications/session/${sessionId}`);
}
