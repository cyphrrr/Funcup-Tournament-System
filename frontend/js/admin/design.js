// admin/design.js — Background CRUD

let opacityTimers = {};

async function loadBackgrounds() {
  const container = document.getElementById('bg-gallery');
  if (!container) return;

  try {
    const bgs = await fetch(`${API_URL}/api/backgrounds`).then(r => r.json());

    if (bgs.length === 0) {
      container.innerHTML = '<em style="color:var(--text-muted)">Noch keine Hintergrundbilder hochgeladen</em>';
      return;
    }

    container.innerHTML = bgs.map(bg => {
      const imgUrl = bg.url.startsWith('http') ? bg.url : `${API_URL}${bg.url}`;
      const date = new Date(bg.uploaded_at).toLocaleDateString('de-DE');
      const isActive = bg.is_active === 1;
      const borderColor = isActive ? '#10b981' : 'var(--border-dark)';
      const borderWidth = isActive ? '3px' : '1px';

      return `
        <div class="bg-card" style="background:var(--bg-section);border:${borderWidth} solid ${borderColor};border-radius:12px;padding:1rem;position:relative">
          <div style="width:100%;height:150px;border-radius:8px;overflow:hidden;margin-bottom:.75rem;background:#000">
            <img src="${imgUrl}" alt="${escapeHtml(bg.original_name)}" style="width:100%;height:100%;object-fit:cover;opacity:${bg.opacity / 100}" loading="lazy">
          </div>
          <div style="font-size:.85rem;font-weight:600;margin-bottom:.25rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${escapeHtml(bg.original_name)}">${escapeHtml(bg.original_name)}</div>
          <div style="font-size:.75rem;color:var(--text-muted);margin-bottom:.75rem">${date}</div>
          <div style="margin-bottom:.75rem">
            <label style="font-size:.75rem;color:var(--text-muted);display:block;margin-bottom:.25rem">Opacity: <span id="opacity-val-${bg.id}">${bg.opacity}%</span></label>
            <input type="range" min="0" max="100" value="${bg.opacity}" style="width:100%;accent-color:var(--primary)" oninput="previewOpacity(${bg.id}, this.value)" onchange="updateOpacity(${bg.id}, this.value)">
          </div>
          <div style="display:flex;gap:.5rem">
            ${isActive
              ? `<button class="btn btn-sm btn-secondary" onclick="deactivateBackground(${bg.id})" style="flex:1">Deaktivieren</button>`
              : `<button class="btn btn-sm btn-primary" onclick="activateBackground(${bg.id})" style="flex:1">Aktivieren</button>`
            }
            <button class="btn btn-sm btn-danger" onclick="deleteBackground(${bg.id})">🗑️</button>
          </div>
          ${isActive ? '<div style="position:absolute;top:.5rem;right:.5rem;background:#10b981;color:#fff;font-size:.7rem;padding:.15rem .5rem;border-radius:4px;font-weight:600">AKTIV</div>' : ''}
        </div>`;
    }).join('');
  } catch (e) {
    container.innerHTML = `<em style="color:var(--danger)">Fehler: ${e.message}</em>`;
  }
}

function previewOpacity(id, value) {
  const label = document.getElementById(`opacity-val-${id}`);
  if (label) label.textContent = `${value}%`;
}

async function updateOpacity(id, value) {
  clearTimeout(opacityTimers[id]);
  opacityTimers[id] = setTimeout(async () => {
    try {
      await authFetch(`${API_URL}/api/backgrounds/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ opacity: parseInt(value) })
      });
      toast('Opacity gespeichert');
    } catch (e) {
      toast('Fehler: ' + e.message, 'error');
    }
  }, 500);
}

async function uploadBackground(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    await authFetch(`${API_URL}/api/backgrounds`, {
      method: 'POST',
      body: formData
    });
    toast('Hintergrundbild hochgeladen!');
    loadBackgrounds();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function activateBackground(id) {
  try {
    await authFetch(`${API_URL}/api/backgrounds/${id}/activate`, { method: 'PATCH' });
    toast('Hintergrundbild aktiviert!');
    loadBackgrounds();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function deactivateBackground(id) {
  try {
    await authFetch(`${API_URL}/api/backgrounds/${id}/deactivate`, { method: 'PATCH' });
    toast('Hintergrundbild deaktiviert');
    loadBackgrounds();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function deleteBackground(id) {
  if (!confirm('Hintergrundbild wirklich löschen?')) return;

  try {
    await authFetch(`${API_URL}/api/backgrounds/${id}`, { method: 'DELETE' });
    toast('Hintergrundbild gelöscht');
    loadBackgrounds();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

// Drag & Drop + File Input Setup
document.addEventListener('DOMContentLoaded', () => {
  const dropArea = document.getElementById('bg-upload-area');
  const fileInput = document.getElementById('bg-file-input');

  if (!dropArea || !fileInput) return;

  ['dragenter', 'dragover'].forEach(evt => {
    dropArea.addEventListener(evt, e => {
      e.preventDefault();
      dropArea.style.borderColor = '#10b981';
      dropArea.style.background = 'rgba(16,185,129,.08)';
    });
  });

  ['dragleave', 'drop'].forEach(evt => {
    dropArea.addEventListener(evt, e => {
      e.preventDefault();
      dropArea.style.borderColor = 'var(--border-dark)';
      dropArea.style.background = 'var(--bg-elevated)';
    });
  });

  dropArea.addEventListener('drop', e => {
    const files = e.dataTransfer.files;
    if (files.length > 0) uploadBackground(files[0]);
  });

  dropArea.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      uploadBackground(fileInput.files[0]);
      fileInput.value = '';
    }
  });
});
