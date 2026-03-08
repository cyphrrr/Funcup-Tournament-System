// admin/news.js — News CRUD

async function loadNews() {
  try {
    const news = await fetch(`${API_URL}/api/news?published_only=false`).then(r => r.json());

    if (news.length === 0) {
      document.getElementById('news-list').innerHTML = '<em style="color:var(--text-muted)">Noch keine Artikel vorhanden</em>';
      return;
    }

    let html = '<table><thead><tr><th>Titel</th><th>Autor</th><th>Status</th><th>Datum</th><th>Aktionen</th></tr></thead><tbody>';

    news.forEach(n => {
      const date = new Date(n.created_at).toLocaleDateString('de-DE');
      const status = n.published ? '<span style="color:var(--success)">✓ Online</span>' : '<span style="color:var(--text-muted)">Entwurf</span>';
      html += `
        <tr>
          <td><strong>${escapeHtml(n.title)}</strong></td>
          <td>${escapeHtml(n.author)}</td>
          <td>${status}</td>
          <td>${date}</td>
          <td>
            <button class="btn btn-sm btn-secondary" onclick="showNewsEditor(${n.id})">✏️</button>
            <button class="btn btn-sm btn-danger" onclick="deleteNews(${n.id})">🗑️</button>
          </td>
        </tr>`;
    });

    html += '</tbody></table>';
    document.getElementById('news-list').innerHTML = html;
  } catch (e) {
    document.getElementById('news-list').innerHTML = `<em style="color:var(--danger)">Fehler: ${e.message}</em>`;
  }
}

async function saveNews() {
  const editId = document.getElementById('news-edit-id').value;
  const title = document.getElementById('news-title').value.trim();
  const content = document.getElementById('news-content').value.trim();
  const author = document.getElementById('news-author').value.trim() || 'Admin';
  const published = parseInt(document.getElementById('news-published').value);

  if (!title || !content) {
    toast('Titel und Inhalt erforderlich', 'error');
    return;
  }

  try {
    if (editId) {
      await authFetch(`${API_URL}/api/news/${editId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content, author, published })
      });
      toast('Artikel aktualisiert!');
    } else {
      await authFetch(`${API_URL}/api/news`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content, author, published })
      });
      toast('Artikel veröffentlicht!');
    }

    showNewsList();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function editNews(id) {
  try {
    const news = await fetch(`${API_URL}/api/news/${id}`).then(r => r.json());
    document.getElementById('news-edit-id').value = news.id;
    document.getElementById('news-title').value = news.title;
    document.getElementById('news-content').value = news.content;
    document.getElementById('news-author').value = news.author;
    document.getElementById('news-published').value = news.published;

    document.getElementById('news-title').focus();
    toast('Artikel zum Bearbeiten geladen');
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

async function deleteNews(id) {
  if (!confirm('Artikel wirklich löschen?')) return;

  try {
    await authFetch(`${API_URL}/api/news/${id}`, { method: 'DELETE' });
    toast('Artikel gelöscht');
    loadNews();
  } catch (e) {
    toast('Fehler: ' + e.message, 'error');
  }
}

function clearNewsForm() {
  document.getElementById('news-edit-id').value = '';
  document.getElementById('news-title').value = '';
  document.getElementById('news-content').value = '';
  document.getElementById('news-author').value = 'Admin';
  document.getElementById('news-published').value = '1';
}

function showNewsEditor(editId = null) {
  document.getElementById('news-list-view').style.display = 'none';
  document.getElementById('news-editor-view').style.display = 'block';

  if (editId) {
    document.getElementById('news-editor-title').textContent = '✏️ Artikel bearbeiten';
    editNews(editId);
  } else {
    document.getElementById('news-editor-title').textContent = '✏️ Neuer Artikel';
    clearNewsForm();
  }
  loadMatchInserterSeasons();
}

function showNewsList() {
  document.getElementById('news-editor-view').style.display = 'none';
  document.getElementById('news-list-view').style.display = 'block';
  clearNewsForm();
  loadNews();
}
