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

export function initBackendStatus() {
  const statusDot = document.getElementById('backend-status-dot');
  const statusText = document.getElementById('backend-status-text');
  if (!statusDot || !statusText) return;

  function update() {
    fetch(`${API_URL}/api/seasons`).then(r => {
      statusDot.className = r.ok ? 'status-dot online' : 'status-dot offline';
      statusText.textContent = r.ok ? 'Backend verbunden' : 'Backend getrennt';
    }).catch(() => {
      statusDot.className = 'status-dot offline';
      statusText.textContent = 'Backend getrennt';
    });
  }

  update();
  setInterval(update, 30000);
}
