import { initBurgerMenu, initAdminLink, initBackendStatus } from './shared-ui.js';
import { API_URL } from './config.js';

class FTSLayout extends HTMLElement {
  connectedCallback() {
    if (this._initialized) return;
    this._initialized = true;

    const pageTitle = this.getAttribute('page-title') || '';

    // Collect existing children before we modify the DOM
    const children = [...this.childNodes];

    // Build the layout
    this.innerHTML = '';

    // Header
    const header = document.createElement('header');
    header.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div style="display:flex;align-items:center;gap:1rem">
          <a href="index.html" style="text-decoration:none"><img src="img/logo_comic.png" alt="BIW Pokal Logo" style="height:50px;width:auto"></a>
          <div>
            <h1 style="font-family:'Outfit',sans-serif;font-size:1.3rem;font-weight:800;letter-spacing:-0.02em;margin:0;display:flex;align-items:center;gap:0.4rem">
              <span style="color:var(--text)">BIW</span><span style="color:var(--primary)">Pokal</span><span style="opacity:0.4;font-weight:400;font-size:1rem;margin-left:0.3rem">${pageTitle}</span>
            </h1>
            <p style="margin:0.15rem 0 0;font-family:'DM Sans',sans-serif;font-size:.8rem;color:var(--muted)">Die Besten im Westen</p>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:1rem">
          <input type="checkbox" class="dark-mode-toggle" id="dark-mode-toggle" aria-label="Dark Mode">
          <button class="burger-btn" id="burger-btn" aria-label="Men\u00fc \u00f6ffnen">
            <span></span><span></span><span></span>
          </button>
        </div>
      </div>`;
    this.appendChild(header);

    // Menu overlay
    const overlay = document.createElement('div');
    overlay.className = 'menu-overlay';
    overlay.id = 'menu-overlay';
    this.appendChild(overlay);

    // Nav
    const nav = document.createElement('nav');
    nav.id = 'nav-menu';
    nav.innerHTML = `
      <ul>
        <li><a href="index.html">Start</a></li>
        <li><a href="regeln.html">Regeln</a></li>
        <li style="border-top:1px solid var(--border);margin-top:.5rem;padding-top:.5rem"><a href="dashboard.html">Mein Profil</a></li>
        <li style="border-top:1px solid var(--border);margin-top:.5rem;padding-top:.5rem"><a href="turnier.html">Gruppenphase</a></li>
        <li><a href="ko.html">KO\u2011Phase</a></li>
        <li style="border-top:1px solid var(--border);margin-top:.5rem;padding-top:.5rem"><a href="ewige-tabelle.html">Ewige Tabelle</a></li>
        <li><a href="archiv.html">Archiv</a></li>
        <li id="admin-link" style="display:none;border-top:1px solid var(--border);margin-top:.5rem;padding-top:.5rem"><a href="admin.html" style="color:var(--primary);font-weight:600">\ud83d\udd10 Admin</a></li>
      </ul>`;
    this.appendChild(nav);

    // Active nav link
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    nav.querySelectorAll('a').forEach(link => {
      if (link.getAttribute('href') === currentPath) link.classList.add('active');
    });

    // Main — move original children here
    const main = document.createElement('main');
    children.forEach(child => main.appendChild(child));
    this.appendChild(main);

    // Footer
    const footer = document.createElement('footer');
    footer.innerHTML = `
      <div class="footer-left">
        <div class="backend-status">
          <span class="status-dot online" id="backend-status-dot"></span>
          <span id="backend-status-text">Backend verbunden</span>
        </div>
      </div>
      <div class="footer-center">
        <p style="margin:0">\u00a9 2026 BIW Pokal | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a></p>
      </div>
      <div class="footer-right" style="display:flex;align-items:center;gap:0.75rem;justify-content:flex-end">
        <span id="app-version" style="font-size:.75rem;opacity:.6"></span>
        <label for="theme-select" style="font-size:.8rem;color:var(--muted)">Theme:</label>
        <select id="theme-select"></select>
      </div>`;
    this.appendChild(footer);

    // Initialize shared UI
    initBurgerMenu();
    initAdminLink();
    initBackendStatus();

    // Version display
    const versionEl = document.getElementById('app-version');
    if (versionEl) {
      fetch(`${API_URL}/api/version`)
        .then(r => r.json())
        .then(data => {
          versionEl.textContent = `v${data.version}`;
          versionEl.title = `${data.app} ${data.version} (${data.status})`;
        })
        .catch(() => { versionEl.textContent = ''; });
    }

    // Page tracking
    fetch(`${API_URL}/api/track`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: window.location.pathname })
    }).catch(() => {});
  }
}

customElements.define('fts-layout', FTSLayout);
