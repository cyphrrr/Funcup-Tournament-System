// api.js — Fetch-Wrapper für BIW Pokal Admin

let authToken = localStorage.getItem('biw_token');

function authHeaders() {
  return authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
}

async function authFetch(url, options = {}) {
  const headers = { ...authHeaders(), ...(options.headers || {}) };
  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    logout();
    throw new Error('Session abgelaufen');
  }

  return res;
}

async function fetchAPI(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const res = await authFetch(`${API_URL}/api${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(err || `HTTP ${res.status}`);
  }
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}
