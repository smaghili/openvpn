const API_BASE = '/api';

function authHeaders() {
  const token = localStorage.getItem('token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({ 'Content-Type': 'application/json' }, authHeaders(), options.headers || {});
  const response = await fetch(`${API_BASE}${path}`, Object.assign({}, options, { headers }));
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || data.error || 'API error');
  }
  return data;
}

async function apiLogin(username, password) {
  const data = await apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
    headers: { 'Content-Type': 'application/json' }
  });
  if (data.token) {
    localStorage.setItem('token', data.token);
  }
  return data;
}

const UsersAPI = {
  list: () => apiFetch('/users'),
  create: (username, password = '') => apiFetch('/users', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  }),
  remove: (username) => apiFetch(`/users/${encodeURIComponent(username)}`, { method: 'DELETE' }),
  setQuota: (username, quotaGb) => apiFetch(`/quota/${encodeURIComponent(username)}`, {
    method: 'PUT',
    body: JSON.stringify({ quota_gb: quotaGb })
  })
};

const AdminsAPI = {
  create: (username, password, role) => apiFetch('/admins', {
    method: 'POST',
    body: JSON.stringify({ username, password, role })
  })
};
