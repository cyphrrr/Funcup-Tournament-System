const THEMES = {
  "flutlicht": {
    label: "🏟️ Stadion bei Flutlicht",
    light: {
      "--bg": "#dce3ea",
      "--card": "#f0f3f7",
      "--card-alt": "#e4e9f0",
      "--border": "#7a8799",
      "--text": "#0c1117",
      "--muted": "#3d4554",
      "--primary": "#b8860b",
      "--accent": "#e5a00d",
      "--success": "#2da044",
      "--danger": "#cf222e",
      "--warning": "#d4880d",
      "--bg-pattern-opacity": "0.18",
      "--bg-pattern-filter": "brightness(1.1) sepia(1) hue-rotate(15deg) saturate(3)"
    },
    dark: {
      "--bg": "#0c1117",
      "--card": "#161b22",
      "--card-alt": "#1c2128",
      "--border": "#454e5c",
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
      "--bg": "#ece5d8",
      "--card": "#faf6ed",
      "--card-alt": "#efe8dc",
      "--border": "#8a7a68",
      "--text": "#2d3a2e",
      "--muted": "#4e5446",
      "--primary": "#1f5c3f",
      "--accent": "#e0d7c2",
      "--success": "#2e7d55",
      "--danger": "#b91c1c",
      "--warning": "#c56a00",
      "--bg-pattern-opacity": "0.18",
      "--bg-pattern-filter": "brightness(1.1) sepia(1) hue-rotate(70deg) saturate(2)"
    },
    dark: {
      "--bg": "#1a1c17",
      "--card": "#252820",
      "--card-alt": "#2d3028",
      "--border": "#545846",
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
      "--bg": "#e2e6ec",
      "--card": "#f5f6f9",
      "--card-alt": "#e0e5ee",
      "--border": "#747f8e",
      "--text": "#1a1f36",
      "--muted": "#414d60",
      "--primary": "#1a3fba",
      "--accent": "#e0e5ee",
      "--success": "#0a7b70",
      "--danger": "#c93816",
      "--warning": "#c93816",
      "--bg-pattern-opacity": "0.16",
      "--bg-pattern-filter": "brightness(1.1) sepia(1) hue-rotate(200deg) saturate(3)"
    },
    dark: {
      "--bg": "#0d0f18",
      "--card": "#161929",
      "--card-alt": "#1c2038",
      "--border": "#3e4465",
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
      "--bg": "#e6ede9",
      "--card": "#f2f8f4",
      "--card-alt": "#ddeee3",
      "--border": "#5e9476",
      "--text": "#1a2e24",
      "--muted": "#3a5448",
      "--primary": "#047857",
      "--accent": "#ddeee3",
      "--success": "#0f8a3c",
      "--danger": "#b91c1c",
      "--warning": "#c56a00",
      "--bg-pattern-opacity": "0.17",
      "--bg-pattern-filter": "brightness(1.1) sepia(1) hue-rotate(100deg) saturate(3)"
    },
    dark: {
      "--bg": "#0c1410",
      "--card": "#141f1a",
      "--card-alt": "#1a2b22",
      "--border": "#325242",
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
      "--bg": "#e0eaed",
      "--card": "#f0f6f8",
      "--card-alt": "#d8e8ec",
      "--border": "#5c8c98",
      "--text": "#122830",
      "--muted": "#365460",
      "--primary": "#0a7d72",
      "--accent": "#d8e8ec",
      "--success": "#0a7d72",
      "--danger": "#c93816",
      "--warning": "#c93816",
      "--bg-pattern-opacity": "0.16",
      "--bg-pattern-filter": "brightness(1.1) sepia(1) hue-rotate(140deg) saturate(3)"
    },
    dark: {
      "--bg": "#0a1214",
      "--card": "#111d21",
      "--card-alt": "#162529",
      "--border": "#2c5560",
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
  "atlantic-night": {
    label: "🌊 Atlantic Night",
    dark: {
      "--bg": "#06111f",
      "--card": "#0d1e35",
      "--card-alt": "#122440",
      "--border": "#2e5282",
      "--text": "#e2eeff",
      "--muted": "#6a8fb5",
      "--primary": "#22c55e",
      "--accent": "#38bdf8",
      "--link": "#38bdf8",
      "--success": "#22c55e",
      "--danger": "#f97316",
      "--warning": "#f97316",
      "--bg-pattern-opacity": "0.13",
      "--bg-pattern-filter": "brightness(2) sepia(1) hue-rotate(220deg) saturate(3)"
    }
  },
  "derby-night": {
    label: "🌙 Derby Night",
    light: {
      "--bg": "#e0e4ec",
      "--card": "#f0f2f8",
      "--card-alt": "#dce0ea",
      "--border": "#6e7e98",
      "--text": "#141b2d",
      "--muted": "#3c4660",
      "--primary": "#0f8a3c",
      "--accent": "#dce0ea",
      "--success": "#0f8a3c",
      "--danger": "#b91c1c",
      "--warning": "#c56a00",
      "--bg-pattern-opacity": "0.16",
      "--bg-pattern-filter": "brightness(1.1) sepia(1) hue-rotate(190deg) saturate(2)"
    },
    dark: {
      "--bg": "#090c14",
      "--card": "#111827",
      "--card-alt": "#162036",
      "--border": "#2c406a",
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
