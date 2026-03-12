import { API_URL } from './config.js';

(async () => {
  try {
    const res = await fetch(`${API_URL}/api/backgrounds/active`);
    if (res.status === 204 || !res.ok) return;

    const bg = await res.json();
    const url = bg.url.startsWith('http') ? bg.url : `${API_URL}${bg.url}`;
    const opacity = bg.opacity / 100;

    const style = document.createElement('style');
    style.textContent = `
      body::before {
        background: url('${url}') center/cover no-repeat fixed !important;
        opacity: ${opacity} !important;
        filter: none !important;
      }
    `;
    document.head.appendChild(style);
  } catch (e) {
    // Fehler ignorieren — Standard-Pattern bleibt bestehen
  }
})();
