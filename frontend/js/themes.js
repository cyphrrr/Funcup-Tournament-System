const THEMES = {
  "flutlicht": {
    label: "🏟️ Stadion bei Flutlicht",
    light: {
      "--bg": "#e8ecf0",
      "--card": "#f5f7fa",
      "--card-alt": "#edf0f5",
      "--border": "#cdd4de",
      "--text": "#0c1117",
      "--muted": "#5a6270",
      "--primary": "#b8860b",
      "--accent": "#e5a00d",
      "--success": "#3fb950",
      "--danger": "#f85149",
      "--warning": "#e5a00d",
      "--bg-pattern-opacity": "0.06",
      "--bg-pattern-filter": "brightness(0.3) sepia(1) hue-rotate(15deg) saturate(3)"
    },
    dark: {
      "--bg": "#0c1117",
      "--card": "#161b22",
      "--card-alt": "#1c2128",
      "--border": "#30363d",
      "--text": "#e6edf3",
      "--muted": "#7d8590",
      "--primary": "#e5a00d",
      "--accent": "#e5a00d",
      "--success": "#3fb950",
      "--danger": "#f85149",
      "--warning": "#e5a00d",
      "--bg-pattern-opacity": "0.12",
      "--bg-pattern-filter": "brightness(2) sepia(1) hue-rotate(15deg) saturate(2)"
    }
  },
  "vereinsheim": {
    label: "🍺 Vereinsheim",
    light: {
      "--bg": "#f5f0e8",
      "--card": "#fffdf7",
      "--card-alt": "#f7f2ea",
      "--border": "#ddd5c4",
      "--text": "#2d3a2e",
      "--muted": "#7a8072",
      "--primary": "#2d6a4f",
      "--accent": "#eae3d2",
      "--success": "#40916c",
      "--danger": "#c44536",
      "--warning": "#d97706",
      "--bg-pattern-opacity": "0.07",
      "--bg-pattern-filter": "brightness(0.3) sepia(1) hue-rotate(70deg) saturate(2)"
    },
    dark: {
      "--bg": "#1a1c17",
      "--card": "#252820",
      "--card-alt": "#2d3028",
      "--border": "#3d4035",
      "--text": "#e8e4da",
      "--muted": "#9a977e",
      "--primary": "#6ab88a",
      "--accent": "#2d3028",
      "--success": "#40916c",
      "--danger": "#e07a5f",
      "--warning": "#d97706",
      "--bg-pattern-opacity": "0.10",
      "--bg-pattern-filter": "brightness(1.5) sepia(1) hue-rotate(70deg) saturate(1.5)"
    }
  },
  "retro": {
    label: "📺 Retro Scoreboard",
    light: {
      "--bg": "#f0f2f5",
      "--card": "#ffffff",
      "--card-alt": "#eef1f6",
      "--border": "#e3e8ee",
      "--text": "#1a1f36",
      "--muted": "#697386",
      "--primary": "#1d4ed8",
      "--accent": "#eef1f6",
      "--success": "#0d9488",
      "--danger": "#e55b2b",
      "--warning": "#e55b2b",
      "--bg-pattern-opacity": "0.05",
      "--bg-pattern-filter": "brightness(0.3) sepia(1) hue-rotate(200deg) saturate(3)"
    },
    dark: {
      "--bg": "#0d0f18",
      "--card": "#161929",
      "--card-alt": "#1c2038",
      "--border": "#2a2f4a",
      "--text": "#e0e4f0",
      "--muted": "#7b82a0",
      "--primary": "#6388f0",
      "--accent": "#1c2038",
      "--success": "#2dd4bf",
      "--danger": "#f0784a",
      "--warning": "#f0784a",
      "--bg-pattern-opacity": "0.12",
      "--bg-pattern-filter": "brightness(2) sepia(1) hue-rotate(200deg) saturate(2)"
    }
  },
  "pitch-green": {
    label: "🌿 Pitch Green",
    light: {
      "--bg": "#f6f8f7",
      "--card": "#ffffff",
      "--card-alt": "#f0faf4",
      "--border": "#d4e5dc",
      "--text": "#1a2e24",
      "--muted": "#5f7a6b",
      "--primary": "#059669",
      "--accent": "#eef2ff",
      "--success": "#16a34a",
      "--danger": "#dc2626",
      "--warning": "#d97706",
      "--bg-pattern-opacity": "0.06",
      "--bg-pattern-filter": "brightness(0.3) sepia(1) hue-rotate(100deg) saturate(3)"
    },
    dark: {
      "--bg": "#0c1410",
      "--card": "#141f1a",
      "--card-alt": "#1a2b22",
      "--border": "#243d30",
      "--text": "#e4efe8",
      "--muted": "#7fa892",
      "--primary": "#34d399",
      "--accent": "#1a2b22",
      "--success": "#34d399",
      "--danger": "#f87171",
      "--warning": "#fbbf24",
      "--bg-pattern-opacity": "0.12",
      "--bg-pattern-filter": "brightness(2) sepia(1) hue-rotate(100deg) saturate(2)"
    }
  },
  "stadium-electric": {
    label: "⚡ Stadium Electric",
    light: {
      "--bg": "#f4f7f8",
      "--card": "#ffffff",
      "--card-alt": "#eef6f8",
      "--border": "#d0dfe4",
      "--text": "#122830",
      "--muted": "#5a7882",
      "--primary": "#0d9488",
      "--accent": "#eef6f8",
      "--success": "#0d9488",
      "--danger": "#ea580c",
      "--warning": "#ea580c",
      "--bg-pattern-opacity": "0.05",
      "--bg-pattern-filter": "brightness(0.3) sepia(1) hue-rotate(140deg) saturate(3)"
    },
    dark: {
      "--bg": "#0a1214",
      "--card": "#111d21",
      "--card-alt": "#162529",
      "--border": "#1e3a42",
      "--text": "#dceef2",
      "--muted": "#6da3b0",
      "--primary": "#2dd4bf",
      "--accent": "#162529",
      "--success": "#2dd4bf",
      "--danger": "#fb923c",
      "--warning": "#fb923c",
      "--bg-pattern-opacity": "0.13",
      "--bg-pattern-filter": "brightness(2) sepia(1) hue-rotate(140deg) saturate(2.5)"
    }
  },
  "derby-night": {
    label: "🌙 Derby Night",
    light: {
      "--bg": "#f0f2f5",
      "--card": "#ffffff",
      "--card-alt": "#edf0f7",
      "--border": "#cfd5e0",
      "--text": "#141b2d",
      "--muted": "#5b6580",
      "--primary": "#16a34a",
      "--accent": "#edf0f7",
      "--success": "#16a34a",
      "--danger": "#dc2626",
      "--warning": "#d97706",
      "--bg-pattern-opacity": "0.05",
      "--bg-pattern-filter": "brightness(0.3) sepia(1) hue-rotate(190deg) saturate(2)"
    },
    dark: {
      "--bg": "#090c14",
      "--card": "#111827",
      "--card-alt": "#162036",
      "--border": "#1e2d4a",
      "--text": "#dfe4ed",
      "--muted": "#7889a8",
      "--primary": "#4ade80",
      "--accent": "#162036",
      "--success": "#4ade80",
      "--danger": "#f87171",
      "--warning": "#fbbf24",
      "--bg-pattern-opacity": "0.14",
      "--bg-pattern-filter": "brightness(2.5) sepia(1) hue-rotate(190deg) saturate(2)"
    }
  }
};

const DEFAULT_THEME = "flutlicht";

function applyTheme(themeId, mode) {
  const theme = THEMES[themeId];
  if (!theme) return;
  const vars = theme[mode];
  if (!vars) return;
  const root = document.documentElement;
  Object.entries(vars).forEach(([prop, val]) => {
    root.style.setProperty(prop, val);
  });
}

function getStoredTheme() {
  return localStorage.getItem('biw_theme') || DEFAULT_THEME;
}

function getStoredMode() {
  return localStorage.getItem('biw_dark_mode') === 'true' ? 'dark' : 'light';
}

function setTheme(themeId) {
  localStorage.setItem('biw_theme', themeId);
  applyTheme(themeId, getStoredMode());
}

function setMode(isDark) {
  localStorage.setItem('biw_dark_mode', isDark ? 'true' : 'false');
  applyTheme(getStoredTheme(), isDark ? 'dark' : 'light');
}

function initThemeSystem() {
  // Sofort beim Laden anwenden (kein Flash)
  applyTheme(getStoredTheme(), getStoredMode());

  // Footer-Dropdown befüllen
  const dropdown = document.getElementById('theme-select');
  if (dropdown) {
    const currentTheme = getStoredTheme();
    Object.entries(THEMES).forEach(([id, t]) => {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = t.label;
      if (id === currentTheme) opt.selected = true;
      dropdown.appendChild(opt);
    });
    dropdown.addEventListener('change', (e) => setTheme(e.target.value));
  }

  // Dark-Mode-Toggle anpassen
  const toggle = document.getElementById('dark-mode-toggle');
  if (toggle) {
    toggle.checked = getStoredMode() === 'dark';
    toggle.addEventListener('change', () => setMode(toggle.checked));
  }
}

// Auto-Init wenn DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initThemeSystem);
} else {
  initThemeSystem();
}
