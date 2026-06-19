"""
Interface d'administration — API + SPA HTML.

GET  /admin/                              → SPA admin (HTML)
GET  /admin/api/catalogues               → liste avec visibilité (admin)
PUT  /admin/api/catalogues/{slug}/visibility → met à jour la visibilité (admin)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from models.catalogue import CatalogueVisibility
import db.repository as repo
import db.user_repository as user_repo
from api.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["Administration"])


# ---------------------------------------------------------------------------
# API JSON (admin only)
# ---------------------------------------------------------------------------

@router.get("/api/catalogues", summary="Catalogues avec visibilité (admin)")
async def list_catalogues_admin(_: dict = Depends(require_admin)):
    items = await repo.get_all_summary()
    # Enrichir avec la visibilité stockée dans chaque doc
    result = []
    for item in items:
        doc = await repo.find_by_slug(item["slug"])
        if doc:
            result.append({
                "slug":       doc.get("slug"),
                "nom":        doc.get("nom"),
                "saisons":    [{"slug": s.get("slug"), "nom": s.get("nom"), "lang": s.get("lang")}
                               for s in doc.get("saisons", [])],
                "films":      [{"slug": f.get("slug"), "nom": f.get("nom"), "lang": f.get("lang")}
                               for f in doc.get("films", [])],
                "scans":      [{"slug": s.get("slug"), "nom": s.get("nom")}
                               for s in doc.get("scans", [])],
                "visibility": doc.get("visibility", {
                    "is_public": True,
                    "public_saisons": [],
                    "public_films": [],
                    "public_scans": [],
                }),
            })
    return result


@router.put(
    "/api/catalogues/{slug}/visibility",
    summary="Mettre à jour la visibilité d'un catalogue (admin)",
)
async def update_visibility(
    slug:       str,
    body:       CatalogueVisibility,
    _:          dict = Depends(require_admin),
):
    found = await repo.update_catalogue_visibility(slug, body.model_dump())
    if not found:
        raise HTTPException(404, f"Catalogue '{slug}' introuvable")
    return {"ok": True, "slug": slug, "visibility": body.model_dump()}


# ---------------------------------------------------------------------------
# SPA HTML — accessible sans authentification (la page gère le login elle-même)
# ---------------------------------------------------------------------------

_ADMIN_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Anime Sama — Administration</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#0f1117;color:#e2e8f0}
.sidebar{width:220px;min-height:100vh;background:#1a1d27;border-right:1px solid #2d3148}
.sidebar .nav-link{color:#94a3b8;border-radius:6px}
.sidebar .nav-link:hover,.sidebar .nav-link.active{background:#2d3148;color:#fff}
.content{flex:1;padding:2rem;overflow-y:auto}
.card{background:#1a1d27;border:1px solid #2d3148}
.table{--bs-table-bg:transparent;--bs-table-border-color:#2d3148;--bs-table-color:#e2e8f0}
.table tbody tr:hover{background:#2d3148}
.badge-admin{background:#7c3aed}
.badge-user{background:#0284c7}
.modal-content{background:#1a1d27;border:1px solid #2d3148;color:#e2e8f0}
.modal-header,.modal-footer{border-color:#2d3148}
.form-control,.form-select,.form-check-input{background:#0f1117;border-color:#2d3148;color:#e2e8f0}
.form-control:focus,.form-select:focus{background:#0f1117;color:#e2e8f0;border-color:#7c3aed;box-shadow:none}
.form-check-input:checked{background-color:#7c3aed;border-color:#7c3aed}
.btn-primary{background:#7c3aed;border-color:#7c3aed}
.btn-primary:hover{background:#6d28d9;border-color:#6d28d9}
.tag{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.75rem;margin:2px;background:#2d3148}
#login-page{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0f1117}
.login-card{width:380px}
</style>
</head>
<body>

<!-- LOGIN -->
<div id="login-page">
  <div class="card login-card p-4 shadow-lg">
    <h4 class="mb-4 text-center fw-bold">
      <span class="text-purple" style="color:#7c3aed">Anime Sama</span> Admin
    </h4>
    <div id="login-error" class="alert alert-danger d-none"></div>
    <div class="mb-3">
      <label class="form-label">Nom d'utilisateur</label>
      <input id="inp-username" type="text" class="form-control" placeholder="admin">
    </div>
    <div class="mb-3">
      <label class="form-label">Mot de passe</label>
      <input id="inp-password" type="password" class="form-control">
    </div>
    <button id="btn-login" class="btn btn-primary w-100">Connexion</button>
  </div>
</div>

<!-- ADMIN PANEL -->
<div id="admin-page" class="d-flex" style="display:none!important">
  <!-- Sidebar -->
  <div class="sidebar p-3 d-flex flex-column">
    <div class="mb-4">
      <div class="fw-bold" style="color:#7c3aed;font-size:1.1rem">Anime Sama</div>
      <small class="text-muted">Administration</small>
    </div>
    <nav class="nav flex-column gap-1 flex-grow-1">
      <a href="#" class="nav-link active" onclick="showTab('users')">👥 Utilisateurs</a>
      <a href="#" class="nav-link" onclick="showTab('catalogues')">📚 Catalogues</a>
    </nav>
    <div class="mt-auto">
      <small id="logged-as" class="text-muted d-block mb-2"></small>
      <button class="btn btn-sm btn-outline-secondary w-100" onclick="logout()">Déconnexion</button>
    </div>
  </div>

  <!-- Content -->
  <div class="content">
    <!-- USERS TAB -->
    <div id="tab-users">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h5 class="mb-0 fw-bold">Utilisateurs</h5>
        <button class="btn btn-primary btn-sm" onclick="openCreateUser()">+ Nouvel utilisateur</button>
      </div>
      <div class="card">
        <div class="table-responsive">
          <table class="table table-hover mb-0">
            <thead><tr>
              <th>Utilisateur</th><th>Rôle</th><th>Actif</th>
              <th>Sync</th><th>Suppr.</th><th>Refresh</th>
              <th>Catalogues</th><th>Actions</th>
            </tr></thead>
            <tbody id="users-tbody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- CATALOGUES TAB -->
    <div id="tab-catalogues" class="d-none">
      <h5 class="mb-4 fw-bold">Visibilité des catalogues</h5>
      <div id="catalogues-list" class="row g-3"></div>
    </div>
  </div>
</div>

<!-- MODAL : Créer/Éditer utilisateur -->
<div class="modal fade" id="user-modal" tabindex="-1">
  <div class="modal-dialog modal-lg">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="user-modal-title">Utilisateur</h5>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <div id="user-form-error" class="alert alert-danger d-none"></div>
        <div class="row g-3">
          <div class="col-md-6">
            <label class="form-label">Nom d'utilisateur *</label>
            <input id="f-username" class="form-control">
          </div>
          <div class="col-md-6">
            <label class="form-label">Mot de passe <span id="f-pass-hint" class="text-muted">(laisser vide = inchangé)</span></label>
            <input id="f-password" type="password" class="form-control">
          </div>
          <div class="col-md-6">
            <label class="form-label">Email</label>
            <input id="f-email" type="email" class="form-control">
          </div>
          <div class="col-md-3">
            <label class="form-label">Rôle</label>
            <select id="f-role" class="form-select">
              <option value="user">Utilisateur</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div class="col-md-3 d-flex align-items-end">
            <div class="form-check">
              <input id="f-active" type="checkbox" class="form-check-input" checked>
              <label class="form-check-label">Actif</label>
            </div>
          </div>
        </div>

        <hr style="border-color:#2d3148">
        <h6 class="fw-bold mb-3">Permissions opérationnelles</h6>
        <div class="d-flex gap-4 flex-wrap">
          <div class="form-check">
            <input id="f-can-sync" type="checkbox" class="form-check-input">
            <label class="form-check-label">Synchronisation</label>
          </div>
          <div class="form-check">
            <input id="f-can-delete" type="checkbox" class="form-check-input">
            <label class="form-check-label">Suppression</label>
          </div>
          <div class="form-check">
            <input id="f-can-refresh" type="checkbox" class="form-check-input">
            <label class="form-check-label">Rafraîchissement</label>
          </div>
        </div>

        <hr style="border-color:#2d3148">
        <h6 class="fw-bold mb-3">Accès aux catalogues</h6>
        <div class="form-check mb-3">
          <input id="f-all-cats" type="checkbox" class="form-check-input"
                 onchange="toggleCatList()">
          <label class="form-check-label">Accès à tous les catalogues</label>
        </div>
        <div id="cat-access-section" class="d-none">
          <div id="cat-list-check" class="row g-2 mb-3"></div>
        </div>
        <!-- Contenu détaillé par catalogue -->
        <div id="cat-content-section"></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
        <button class="btn btn-primary" onclick="saveUser()">Enregistrer</button>
      </div>
    </div>
  </div>
</div>

<!-- MODAL : Visibilité catalogue -->
<div class="modal fade" id="visibility-modal" tabindex="-1">
  <div class="modal-dialog modal-lg">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="vis-modal-title">Visibilité</h5>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body" id="vis-modal-body"></div>
      <div class="modal-footer">
        <button class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
        <button class="btn btn-primary" onclick="saveVisibility()">Enregistrer</button>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
// ─── État global ─────────────────────────────────────────────────────────────
let token = localStorage.getItem('anime_admin_token');
let allUsers = [], allCatalogues = [], currentUserEdit = null, currentVisSlug = null;
const userModal = new bootstrap.Modal('#user-modal');
const visModal  = new bootstrap.Modal('#visibility-modal');

// ─── API ─────────────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = {
    method,
    headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  if (r.status === 204) return null;
  const data = await r.json();
  if (!r.ok) throw data.detail || JSON.stringify(data);
  return data;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
document.getElementById('inp-password').addEventListener('keydown', e => {
  if (e.key === 'Enter') doLogin();
});
document.getElementById('btn-login').addEventListener('click', doLogin);

async function doLogin() {
  const u = document.getElementById('inp-username').value.trim();
  const p = document.getElementById('inp-password').value;
  const err = document.getElementById('login-error');
  err.classList.add('d-none');
  try {
    const body = new URLSearchParams({username: u, password: p});
    const r = await fetch('/auth/login', {method:'POST', body});
    const data = await r.json();
    if (!r.ok) throw data.detail;
    token = data.access_token;
    localStorage.setItem('anime_admin_token', token);
    await initAdmin();
  } catch(e) {
    err.textContent = typeof e === 'string' ? e : 'Identifiants incorrects';
    err.classList.remove('d-none');
  }
}

function logout() {
  localStorage.removeItem('anime_admin_token');
  token = null;
  document.getElementById('login-page').style.display = 'flex';
  document.getElementById('admin-page').style.display = 'none';
}

// ─── Init ─────────────────────────────────────────────────────────────────────
async function initAdmin() {
  try {
    const me = await api('GET', '/auth/me');
    if (me.role !== 'admin') { alert('Accès réservé aux administrateurs.'); logout(); return; }
    document.getElementById('logged-as').textContent = `Connecté : ${me.username}`;
    document.getElementById('login-page').style.display = 'none';
    document.getElementById('admin-page').style.removeProperty('display');
    await Promise.all([loadUsers(), loadCatalogues()]);
  } catch(e) { logout(); }
}

if (token) initAdmin();

// ─── Tabs ─────────────────────────────────────────────────────────────────────
function showTab(name) {
  document.querySelectorAll('[id^="tab-"]').forEach(d => d.classList.add('d-none'));
  document.getElementById('tab-' + name).classList.remove('d-none');
  document.querySelectorAll('.sidebar .nav-link').forEach(a => a.classList.remove('active'));
  event.target.classList.add('active');
}

// ─── USERS ────────────────────────────────────────────────────────────────────
async function loadUsers() {
  allUsers = await api('GET', '/auth/users');
  renderUsers();
}

function renderUsers() {
  const tbody = document.getElementById('users-tbody');
  tbody.innerHTML = allUsers.map(u => {
    const cats = u.permissions.allowed_catalogues;
    const catLabel = cats.length === 0 ? '<span class="tag">Tous</span>' :
      cats.map(c => `<span class="tag">${c}</span>`).join('');
    return `<tr>
      <td><strong>${u.username}</strong>${u.email ? `<br><small class="text-muted">${u.email}</small>` : ''}</td>
      <td><span class="badge ${u.role === 'admin' ? 'badge-admin' : 'badge-user'}">${u.role}</span></td>
      <td>${u.is_active ? '✅' : '❌'}</td>
      <td>${u.permissions.can_sync ? '✅' : '–'}</td>
      <td>${u.permissions.can_delete ? '✅' : '–'}</td>
      <td>${u.permissions.can_refresh ? '✅' : '–'}</td>
      <td>${catLabel}</td>
      <td>
        <button class="btn btn-sm btn-outline-light me-1" onclick="openEditUser('${u.username}')">✏️</button>
        <button class="btn btn-sm btn-outline-danger" onclick="deleteUser('${u.username}')">🗑</button>
      </td>
    </tr>`;
  }).join('');
}

function openCreateUser() {
  currentUserEdit = null;
  document.getElementById('user-modal-title').textContent = 'Nouvel utilisateur';
  document.getElementById('f-pass-hint').textContent = '';
  resetUserForm();
  renderCatList([], {});
  userModal.show();
}

function openEditUser(username) {
  currentUserEdit = username;
  const u = allUsers.find(x => x.username === username);
  document.getElementById('user-modal-title').textContent = `Modifier — ${username}`;
  document.getElementById('f-pass-hint').textContent = '(laisser vide = inchangé)';
  document.getElementById('f-username').value  = u.username;
  document.getElementById('f-username').disabled = true;
  document.getElementById('f-password').value  = '';
  document.getElementById('f-email').value     = u.email || '';
  document.getElementById('f-role').value      = u.role;
  document.getElementById('f-active').checked  = u.is_active;
  document.getElementById('f-can-sync').checked   = u.permissions.can_sync;
  document.getElementById('f-can-delete').checked = u.permissions.can_delete;
  document.getElementById('f-can-refresh').checked= u.permissions.can_refresh;
  const allCats = u.permissions.allowed_catalogues.length === 0;
  document.getElementById('f-all-cats').checked = allCats;
  toggleCatList();
  renderCatList(u.permissions.allowed_catalogues, u.permissions.catalogue_content || {});
  document.getElementById('user-form-error').classList.add('d-none');
  userModal.show();
}

function resetUserForm() {
  ['f-username','f-password','f-email'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('f-username').disabled = false;
  document.getElementById('f-role').value = 'user';
  document.getElementById('f-active').checked = true;
  document.getElementById('f-can-sync').checked = false;
  document.getElementById('f-can-delete').checked = false;
  document.getElementById('f-can-refresh').checked = false;
  document.getElementById('f-all-cats').checked = true;
  toggleCatList();
  document.getElementById('user-form-error').classList.add('d-none');
}

function toggleCatList() {
  const allCats = document.getElementById('f-all-cats').checked;
  document.getElementById('cat-access-section').classList.toggle('d-none', allCats);
  if (allCats) document.getElementById('cat-content-section').innerHTML = '';
}

function renderCatList(allowedCats, contentAccess) {
  const container = document.getElementById('cat-list-check');
  container.innerHTML = allCatalogues.map(c => `
    <div class="col-md-4">
      <div class="form-check">
        <input type="checkbox" class="form-check-input cat-check" id="cc-${c.slug}"
               value="${c.slug}" ${allowedCats.includes(c.slug) ? 'checked' : ''}
               onchange="renderContentAccess('${c.slug}', ${JSON.stringify(contentAccess).replace(/'/g, "\\'")})">
        <label class="form-check-label" for="cc-${c.slug}">${c.nom}</label>
      </div>
      <div id="content-access-${c.slug}" class="${allowedCats.includes(c.slug) ? '' : 'd-none'} ms-3 mt-1">
        ${renderContentAccessHtml(c, contentAccess[c.slug] || {})}
      </div>
    </div>
  `).join('');
}

function renderContentAccessHtml(cat, access) {
  const types = [
    {key:'saisons', label:'Saisons', items: cat.saisons},
    {key:'films',   label:'Films',   items: cat.films},
    {key:'scans',   label:'Scans',   items: cat.scans},
  ];
  return types.filter(t => t.items && t.items.length).map(t => {
    const allowed = (access[t.key] || []);
    const allChecked = allowed.length === 0;
    return `<div class="mb-2">
      <small class="text-muted fw-bold">${t.label}</small><br>
      <div class="form-check form-check-inline">
        <input type="checkbox" class="form-check-input" id="all-${t.key}-${cat.slug}"
               ${allChecked ? 'checked' : ''}
               onchange="toggleContentList('${cat.slug}','${t.key}', this.checked)">
        <label class="form-check-label" for="all-${t.key}-${cat.slug}"><small>Tous</small></label>
      </div>
      <div id="list-${t.key}-${cat.slug}" class="${allChecked ? 'd-none' : ''}">
        ${t.items.map(item => `
          <div class="form-check form-check-inline">
            <input type="checkbox" class="form-check-input content-item"
                   data-cat="${cat.slug}" data-type="${t.key}" value="${item.slug}"
                   ${(allChecked || allowed.includes(item.slug)) && !allChecked ? 'checked' : allChecked ? '' : allowed.includes(item.slug) ? 'checked' : ''}>
            <label class="form-check-label"><small>${item.nom || item.slug}${item.lang ? ' ('+item.lang+')' : ''}</small></label>
          </div>`).join('')}
      </div>
    </div>`;
  }).join('');
}

function renderContentAccess(slug, contentAccess) {
  const cb = document.getElementById('cc-' + slug);
  const section = document.getElementById('content-access-' + slug);
  section.classList.toggle('d-none', !cb.checked);
}

function toggleContentList(slug, type, allChecked) {
  document.getElementById(`list-${type}-${slug}`).classList.toggle('d-none', allChecked);
}

async function saveUser() {
  const errEl = document.getElementById('user-form-error');
  errEl.classList.add('d-none');
  try {
    const role        = document.getElementById('f-role').value;
    const allCats     = document.getElementById('f-all-cats').checked;
    const allowedCats = allCats ? [] :
      [...document.querySelectorAll('.cat-check:checked')].map(cb => cb.value);

    // Construire catalogue_content
    const catalogueContent = {};
    if (!allCats) {
      allowedCats.forEach(catSlug => {
        const saisons = [...document.querySelectorAll(
          `.content-item[data-cat="${catSlug}"][data-type="saisons"]:checked`)].map(x=>x.value);
        const films   = [...document.querySelectorAll(
          `.content-item[data-cat="${catSlug}"][data-type="films"]:checked`)].map(x=>x.value);
        const scans   = [...document.querySelectorAll(
          `.content-item[data-cat="${catSlug}"][data-type="scans"]:checked`)].map(x=>x.value);

        const allSaisons = document.getElementById(`all-saisons-${catSlug}`)?.checked;
        const allFilms   = document.getElementById(`all-films-${catSlug}`)?.checked;
        const allScans   = document.getElementById(`all-scans-${catSlug}`)?.checked;

        catalogueContent[catSlug] = {
          saisons: allSaisons ? [] : saisons,
          films:   allFilms   ? [] : films,
          scans:   allScans   ? [] : scans,
        };
      });
    }

    const perms = {
      can_sync:           document.getElementById('f-can-sync').checked,
      can_delete:         document.getElementById('f-can-delete').checked,
      can_refresh:        document.getElementById('f-can-refresh').checked,
      allowed_catalogues: allowedCats,
      catalogue_content:  catalogueContent,
    };

    if (currentUserEdit) {
      const body = {
        is_active:   document.getElementById('f-active').checked,
        role,
        permissions: perms,
      };
      if (document.getElementById('f-email').value) body.email = document.getElementById('f-email').value;
      await api('PUT', `/auth/users/${currentUserEdit}`, body);
    } else {
      const pass = document.getElementById('f-password').value;
      if (!pass) throw 'Le mot de passe est obligatoire';
      await api('POST', '/auth/register', {
        username:    document.getElementById('f-username').value.trim(),
        password:    pass,
        email:       document.getElementById('f-email').value || null,
        role,
        permissions: perms,
      });
    }
    userModal.hide();
    await loadUsers();
  } catch(e) {
    errEl.textContent = typeof e === 'string' ? e : JSON.stringify(e);
    errEl.classList.remove('d-none');
  }
}

async function deleteUser(username) {
  if (!confirm(`Supprimer l'utilisateur "${username}" ?`)) return;
  try {
    await api('DELETE', `/auth/users/${username}`);
    await loadUsers();
  } catch(e) { alert(JSON.stringify(e)); }
}

// ─── CATALOGUES ───────────────────────────────────────────────────────────────
async function loadCatalogues() {
  allCatalogues = await api('GET', '/admin/api/catalogues');
  renderCatalogues();
}

function renderCatalogues() {
  const container = document.getElementById('catalogues-list');
  container.innerHTML = allCatalogues.map(c => {
    const v = c.visibility || {};
    const pub = v.is_public !== false;
    return `<div class="col-md-6 col-lg-4">
      <div class="card h-100">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <h6 class="fw-bold mb-0">${c.nom}</h6>
            <span class="badge ${pub ? 'bg-success' : 'bg-secondary'}">${pub ? 'Public' : 'Privé'}</span>
          </div>
          <small class="text-muted">${c.slug}</small><br>
          <small class="text-muted mt-1 d-block">
            ${c.saisons.length} saison(s) · ${c.films.length} film(s) · ${c.scans.length} scan(s)
          </small>
          ${pub && (v.public_saisons?.length || v.public_films?.length || v.public_scans?.length) ?
            '<small class="text-warning d-block mt-1">⚠ Contenu public restreint</small>' : ''}
        </div>
        <div class="card-footer d-flex justify-content-end" style="border-color:#2d3148">
          <button class="btn btn-sm btn-outline-light" onclick="openVisibility('${c.slug}')">
            ⚙ Visibilité
          </button>
        </div>
      </div>
    </div>`;
  }).join('');
}

function openVisibility(slug) {
  currentVisSlug = slug;
  const cat = allCatalogues.find(c => c.slug === slug);
  const v   = cat.visibility || {is_public:true, public_saisons:[], public_films:[], public_scans:[]};
  document.getElementById('vis-modal-title').textContent = `Visibilité — ${cat.nom}`;

  const makeContentSection = (key, label, items) => {
    if (!items.length) return '';
    const allowed  = v['public_' + key] || [];
    const showAll  = allowed.length === 0;
    return `<div class="mb-3">
      <label class="form-label fw-bold">${label} visibles publiquement</label>
      <div class="form-check mb-1">
        <input type="checkbox" class="form-check-input" id="vis-all-${key}" ${showAll ? 'checked' : ''}
               onchange="document.getElementById('vis-list-${key}').classList.toggle('d-none', this.checked)">
        <label class="form-check-label" for="vis-all-${key}">Tous</label>
      </div>
      <div id="vis-list-${key}" class="${showAll ? 'd-none' : ''} ms-3">
        ${items.map(item => `
          <div class="form-check">
            <input type="checkbox" class="form-check-input vis-item" data-type="${key}"
                   value="${item.slug}" ${allowed.includes(item.slug) ? 'checked' : ''}>
            <label class="form-check-label">${item.nom || item.slug}${item.lang ? ' ('+item.lang+')' : ''}</label>
          </div>`).join('')}
      </div>
    </div>`;
  };

  document.getElementById('vis-modal-body').innerHTML = `
    <div class="mb-4">
      <div class="form-check form-switch">
        <input class="form-check-input" type="checkbox" id="vis-public" ${v.is_public !== false ? 'checked' : ''}
               onchange="document.getElementById('vis-content-section').classList.toggle('d-none', !this.checked)">
        <label class="form-check-label fw-bold" for="vis-public">Catalogue public (accessible sans authentification)</label>
      </div>
      <small class="text-muted">Si désactivé, seuls les utilisateurs authentifiés et autorisés peuvent voir ce catalogue.</small>
    </div>
    <div id="vis-content-section" class="${v.is_public !== false ? '' : 'd-none'}">
      <p class="text-muted mb-3"><small>Choisissez quel contenu est visible pour les utilisateurs non authentifiés.<br>
      "Tous" = tout le contenu du catalogue est public.</small></p>
      ${makeContentSection('saisons', '🎬 Saisons', cat.saisons)}
      ${makeContentSection('films',   '🎞 Films',   cat.films)}
      ${makeContentSection('scans',   '📖 Scans',   cat.scans)}
    </div>
  `;
  visModal.show();
}

async function saveVisibility() {
  const isPublic = document.getElementById('vis-public').checked;
  const getItems = type => {
    const allChecked = document.getElementById(`vis-all-${type}`)?.checked;
    if (allChecked) return [];
    return [...document.querySelectorAll(`.vis-item[data-type="${type}"]:checked`)].map(x => x.value);
  };
  const body = {
    is_public:      isPublic,
    public_saisons: isPublic ? getItems('saisons') : [],
    public_films:   isPublic ? getItems('films')   : [],
    public_scans:   isPublic ? getItems('scans')   : [],
  };
  try {
    await api('PUT', `/admin/api/catalogues/${currentVisSlug}/visibility`, body);
    visModal.hide();
    await loadCatalogues();
  } catch(e) { alert(JSON.stringify(e)); }
}
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_ui():
    """Interface d'administration (SPA)."""
    return HTMLResponse(_ADMIN_HTML)
