import { API_URL } from './config.js';

export function initBurgerMenu() {
  const burgerBtn = document.getElementById('burger-btn');
  const navMenu = document.getElementById('nav-menu');
  const menuOverlay = document.getElementById('menu-overlay');

  function toggleMenu() {
    burgerBtn.classList.toggle('open');
    navMenu.classList.toggle('open');
    menuOverlay.classList.toggle('open');
  }

  burgerBtn.addEventListener('click', toggleMenu);
  menuOverlay.addEventListener('click', toggleMenu);
  navMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      if (navMenu.classList.contains('open')) toggleMenu();
    });
  });
}

export function initAdminLink() {
  if (localStorage.getItem('biw_token')) {
    document.getElementById('admin-link').style.display = 'block';
  }
}

export function setBackendStatus(online) {
  const statusDot = document.getElementById('backend-status-dot');
  const statusText = document.getElementById('backend-status-text');
  if (!statusDot || !statusText) return;
  statusDot.className = online ? 'status-dot online' : 'status-dot offline';
  statusText.textContent = online ? 'Backend verbunden' : 'Backend getrennt';
}

export function initBackendStatus() {
  setInterval(() => {
    fetch(`${API_URL}/api/version`).then(r => {
      setBackendStatus(r.ok);
    }).catch(() => {
      setBackendStatus(false);
    });
  }, 30000);
}
