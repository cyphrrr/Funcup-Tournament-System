/**
 * Zentrale API-Konfiguration für BIW Pokal Frontend
 *
 * Automatische Umgebungserkennung:
 * - Lokal (localhost, 127.0.0.1, 192.168.x.x): Backend auf Port 8000
 * - Production: window.location.origin
 */

export const API_URL = (() => {
  const hostname = window.location.hostname;

  // Lokal-Erkennungslogik
  const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
  const isPrivateNetwork = hostname.startsWith('192.168.') ||
                          hostname.startsWith('10.') ||
                          hostname.startsWith('172.');

  // Wenn lokal: Backend auf Port 8000
  if (isLocalhost || isPrivateNetwork) {
    return `http://${hostname}:8000`;
  }

  // Ansonsten: Production (gleicher Origin wie Frontend)
  return window.location.origin;
})();

// Optional: Debug-Ausgabe (nur in Development)
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  console.log('[BIW Config] API_URL:', API_URL);
}
