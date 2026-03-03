// auth.js — Login/Logout/Auth-Check

function showLogin() {
  document.getElementById('login-overlay').style.display = 'flex';
  document.getElementById('admin-main').style.display = 'none';
}

function hideLogin() {
  document.getElementById('login-overlay').style.display = 'none';
  document.getElementById('admin-main').style.display = 'flex';
}

async function doLogin() {
  const user = document.getElementById('login-user').value;
  const pass = document.getElementById('login-pass').value;
  const errEl = document.getElementById('login-error');

  try {
    const res = await fetch(`${API_URL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: user, password: pass })
    });

    if (!res.ok) {
      errEl.textContent = 'Ungültige Anmeldedaten';
      errEl.style.display = 'block';
      return;
    }

    const data = await res.json();
    authToken = data.access_token;
    localStorage.setItem('biw_token', authToken);
    localStorage.setItem('biw_user', data.username);
    hideLogin();
    loadDashboard();
  } catch (e) {
    errEl.textContent = 'Verbindungsfehler';
    errEl.style.display = 'block';
  }
}

function logout() {
  localStorage.removeItem('biw_token');
  localStorage.removeItem('biw_user');
  authToken = null;
  showLogin();
}

async function checkAuth() {
  if (!authToken) {
    showLogin();
    return;
  }

  try {
    const res = await fetch(`${API_URL}/api/me`, { headers: authHeaders() });
    if (res.ok) {
      hideLogin();
      loadDashboard();
    } else {
      showLogin();
    }
  } catch (e) {
    showLogin();
  }
}
