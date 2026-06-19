"""
Serveur d'administration autonome (port 8001 par défaut).

Lance séparément du serveur principal :
  python admin_main.py
ou :
  uvicorn admin_main:app --port 8001 --reload

L'interface fait ses appels API vers le serveur principal (port 8000).
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

API_BASE   = os.getenv("API_BASE",   "http://localhost:8000")
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8001"))

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# ---------------------------------------------------------------------------
# SPA HTML
# ---------------------------------------------------------------------------

_HTML = r"""<!DOCTYPE html>
<html lang="fr" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Anime Sama · Admin</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<style>
/* ─── Variables de thème ──────────────────────────────────────────── */
:root {
  --bg:           #0f172a;
  --surface:      #1e293b;
  --surface2:     #263043;
  --surface-h:    #2d3f56;
  --border:       #334155;
  --text:         #f1f5f9;
  --text2:        #cbd5e1;
  --muted:        #94a3b8;
  --accent:       #8b5cf6;
  --accent-h:     #7c3aed;
  --ok:           #10b981;
  --warn:         #f59e0b;
  --danger:       #f43f5e;
  --info:         #38bdf8;
  --sidebar-w:    240px;
  --header-h:     56px;
}
[data-theme="light"] {
  --bg:           #f1f5f9;
  --surface:      #ffffff;
  --surface2:     #f8fafc;
  --surface-h:    #e2e8f0;
  --border:       #cbd5e1;
  --text:         #0f172a;
  --text2:        #1e293b;
  --muted:        #64748b;
  --accent:       #7c3aed;
  --accent-h:     #6d28d9;
  --ok:           #059669;
  --warn:         #d97706;
  --danger:       #dc2626;
  --info:         #0284c7;
}

/* ─── Base ────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text); font-family:'Inter',system-ui,sans-serif; }
a { color:var(--accent); text-decoration:none; }
a:hover { color:var(--accent-h); }
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }

/* ─── Layout ──────────────────────────────────────────────────────── */
#shell { display:flex; height:100vh; overflow:hidden; }
#sidebar {
  width:var(--sidebar-w); flex-shrink:0;
  background:var(--surface); border-right:1px solid var(--border);
  display:flex; flex-direction:column; overflow:hidden;
}
#main { flex:1; display:flex; flex-direction:column; min-width:0; overflow:hidden; }
#topbar {
  height:var(--header-h); flex-shrink:0;
  background:var(--surface); border-bottom:1px solid var(--border);
  display:flex; align-items:center; padding:0 1.5rem; gap:1rem;
}
#content { flex:1; overflow-y:auto; padding:1.5rem 2rem; }

/* ─── Sidebar ─────────────────────────────────────────────────────── */
.sb-brand {
  padding:1rem 1rem .75rem;
  border-bottom:1px solid var(--border);
}
.sb-brand .title { font-size:.9rem; font-weight:700; color:var(--accent); }
.sb-brand .sub   { font-size:.72rem; color:var(--muted); }

.sb-nav { flex:1; padding:.75rem .5rem; overflow-y:auto; }
.nav-item {
  display:flex; align-items:center; gap:.6rem;
  padding:.5rem .75rem; border-radius:8px; cursor:pointer;
  color:var(--muted); font-size:.875rem; font-weight:500;
  transition:background .15s, color .15s; user-select:none;
}
.nav-item:hover { background:var(--surface-h); color:var(--text2); }
.nav-item.active { background:rgba(139,92,246,.15); color:var(--accent); }
.nav-item .icon { font-size:1rem; width:20px; text-align:center; }

.sb-footer {
  padding:.75rem 1rem; border-top:1px solid var(--border);
  font-size:.78rem; color:var(--muted);
}
.sb-footer .me { margin-bottom:.4rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

/* ─── Topbar ──────────────────────────────────────────────────────── */
#topbar h1 { font-size:1rem; font-weight:600; margin:0; flex:1; }
.topbar-actions { display:flex; align-items:center; gap:.5rem; }

/* ─── Buttons ─────────────────────────────────────────────────────── */
.btn { border:none; border-radius:8px; font-size:.825rem; font-weight:500;
       padding:.4rem .85rem; cursor:pointer; transition:background .15s, opacity .15s;
       display:inline-flex; align-items:center; gap:.4rem; }
.btn:disabled { opacity:.45; cursor:not-allowed; }
.btn-primary   { background:var(--accent); color:#fff; }
.btn-primary:hover   { background:var(--accent-h); }
.btn-secondary { background:var(--surface2); color:var(--text2); border:1px solid var(--border); }
.btn-secondary:hover { background:var(--surface-h); }
.btn-danger  { background:rgba(244,63,94,.12); color:var(--danger); border:1px solid rgba(244,63,94,.2); }
.btn-danger:hover { background:rgba(244,63,94,.22); }
.btn-ghost   { background:transparent; color:var(--muted); padding:.3rem .5rem; }
.btn-ghost:hover { background:var(--surface2); color:var(--text); }
.btn-icon    { padding:.35rem .45rem; border-radius:6px; }
.btn-sm      { font-size:.78rem; padding:.3rem .65rem; }

/* ─── Filter bar ──────────────────────────────────────────────────── */
.filter-bar {
  display:flex; align-items:center; gap:.6rem; flex-wrap:wrap;
  background:var(--surface); border:1px solid var(--border);
  border-radius:10px; padding:.6rem .9rem; margin-bottom:1rem;
}
.filter-bar input, .filter-bar select {
  background:var(--surface2); border:1px solid var(--border);
  color:var(--text); border-radius:7px; padding:.35rem .7rem; font-size:.825rem;
  outline:none; transition:border .15s;
}
.filter-bar input:focus, .filter-bar select:focus { border-color:var(--accent); }
.filter-bar input { flex:1; min-width:160px; }
.filter-bar select { min-width:130px; }

/* ─── Tables ──────────────────────────────────────────────────────── */
.data-table-wrap { background:var(--surface); border:1px solid var(--border); border-radius:12px; overflow:hidden; }
.data-table { width:100%; border-collapse:collapse; }
.data-table thead tr { background:var(--surface2); }
.data-table thead th {
  padding:.7rem 1rem; font-size:.78rem; font-weight:600;
  color:var(--muted); text-transform:uppercase; letter-spacing:.04em;
  border-bottom:1px solid var(--border); white-space:nowrap;
}
.data-table tbody td { padding:.7rem 1rem; font-size:.85rem; border-bottom:1px solid var(--border); vertical-align:middle; }
.data-table tbody tr:last-child td { border-bottom:none; }
.data-table tbody tr:hover td { background:var(--surface-h); }
.data-table .actions { display:flex; gap:.4rem; }

/* ─── Badges ──────────────────────────────────────────────────────── */
.badge {
  display:inline-block; border-radius:999px; padding:.2rem .6rem;
  font-size:.72rem; font-weight:600; white-space:nowrap;
}
.badge-accent   { background:rgba(139,92,246,.15); color:var(--accent); }
.badge-ok       { background:rgba(16,185,129,.15);  color:var(--ok); }
.badge-warn     { background:rgba(245,158,11,.15);  color:var(--warn); }
.badge-danger   { background:rgba(244,63,94,.15);   color:var(--danger); }
.badge-info     { background:rgba(56,189,248,.15);  color:var(--info); }
.badge-muted    { background:var(--surface2); color:var(--muted); }

/* ─── Avatar initiales ────────────────────────────────────────────── */
.avatar {
  width:32px; height:32px; border-radius:50%; background:rgba(139,92,246,.2);
  color:var(--accent); font-weight:700; font-size:.75rem;
  display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;
}

/* ─── Perm chips ──────────────────────────────────────────────────── */
.perm-chip {
  display:inline-flex; align-items:center; gap:.25rem;
  padding:.15rem .45rem; border-radius:5px; font-size:.72rem; font-weight:500;
  background:var(--surface2); color:var(--muted);
}
.perm-chip.on  { background:rgba(16,185,129,.12); color:var(--ok); }
.perm-chip.off { opacity:.4; }

/* ─── Genre tags ──────────────────────────────────────────────────── */
.tag {
  display:inline-block; padding:.15rem .5rem; border-radius:5px;
  font-size:.72rem; background:var(--surface2); color:var(--text2);
  margin:1px;
}

/* ─── Page header ─────────────────────────────────────────────────── */
.page-header { display:flex; align-items:center; gap:1rem; margin-bottom:1.25rem; }
.page-header h2 { margin:0; font-size:1.15rem; font-weight:700; flex:1; }

/* ─── Empty state ─────────────────────────────────────────────────── */
.empty-state { text-align:center; padding:3rem 1rem; color:var(--muted); }
.empty-state .icon { font-size:2.5rem; margin-bottom:.75rem; }

/* ─── Login ───────────────────────────────────────────────────────── */
#login-page {
  position:fixed; inset:0; background:var(--bg);
  display:flex; align-items:center; justify-content:center; z-index:100;
}
.login-card {
  width:380px; background:var(--surface); border:1px solid var(--border);
  border-radius:16px; padding:2rem; box-shadow:0 20px 60px rgba(0,0,0,.4);
}
.login-card h2 { text-align:center; font-size:1.25rem; font-weight:700; margin-bottom:1.5rem; }
.login-card .logo { color:var(--accent); }

/* ─── Form controls ───────────────────────────────────────────────── */
.form-group { margin-bottom:1rem; }
.form-group label { display:block; font-size:.8rem; font-weight:500; color:var(--text2); margin-bottom:.35rem; }
.form-control, .form-select {
  width:100%; background:var(--surface2); border:1px solid var(--border);
  color:var(--text); border-radius:8px; padding:.5rem .75rem; font-size:.875rem;
  outline:none; transition:border .15s;
}
.form-control:focus, .form-select:focus { border-color:var(--accent); }
.form-control::placeholder { color:var(--muted); }
.form-check { display:flex; align-items:center; gap:.5rem; cursor:pointer; }
.form-check input[type=checkbox] {
  width:16px; height:16px; border-radius:4px; border:2px solid var(--border);
  background:var(--surface2); cursor:pointer; flex-shrink:0;
  accent-color:var(--accent);
}
.form-switch { display:flex; align-items:center; gap:.6rem; cursor:pointer; }
.form-switch input[type=checkbox] {
  width:34px; height:18px; appearance:none; border-radius:999px;
  background:var(--border); cursor:pointer; position:relative; transition:background .2s; flex-shrink:0;
}
.form-switch input[type=checkbox]:checked { background:var(--accent); }
.form-switch input[type=checkbox]::after {
  content:''; position:absolute; width:12px; height:12px;
  background:#fff; border-radius:50%; top:3px; left:3px; transition:left .2s;
}
.form-switch input[type=checkbox]:checked::after { left:19px; }

/* ─── Modals ──────────────────────────────────────────────────────── */
.modal-backdrop {
  position:fixed; inset:0; background:rgba(0,0,0,.6); z-index:200;
  display:flex; align-items:center; justify-content:center; padding:1rem;
}
.modal-box {
  background:var(--surface); border:1px solid var(--border); border-radius:14px;
  width:100%; box-shadow:0 25px 80px rgba(0,0,0,.5);
  display:flex; flex-direction:column; max-height:90vh;
  animation:modal-in .18s ease-out;
}
@keyframes modal-in { from { opacity:0; transform:translateY(10px) scale(.97); } to { opacity:1; transform:none; } }
.modal-box.sm { max-width:480px; }
.modal-box.md { max-width:640px; }
.modal-box.lg { max-width:820px; }
.modal-head {
  display:flex; align-items:center; padding:1rem 1.25rem;
  border-bottom:1px solid var(--border); gap:.75rem; flex-shrink:0;
}
.modal-head h3 { margin:0; font-size:1rem; font-weight:600; flex:1; }
.modal-body { padding:1.25rem; overflow-y:auto; flex:1; }
.modal-foot {
  display:flex; justify-content:flex-end; gap:.6rem; padding:1rem 1.25rem;
  border-top:1px solid var(--border); flex-shrink:0;
}

/* ─── Alert ───────────────────────────────────────────────────────── */
.alert { padding:.6rem .9rem; border-radius:8px; font-size:.825rem; margin-bottom:.75rem; }
.alert-danger  { background:rgba(244,63,94,.1); color:var(--danger); border:1px solid rgba(244,63,94,.2); }
.alert-success { background:rgba(16,185,129,.1); color:var(--ok); border:1px solid rgba(16,185,129,.2); }

/* ─── Section d'accès catalogue ──────────────────────────────────── */
.cat-access-row {
  border:1px solid var(--border); border-radius:10px; overflow:hidden; margin-bottom:.5rem;
}
.cat-access-head {
  display:flex; align-items:center; gap:.75rem; padding:.6rem .9rem;
  background:var(--surface2); cursor:pointer; user-select:none;
}
.cat-access-head:hover { background:var(--surface-h); }
.cat-access-body { padding:.75rem .9rem; border-top:1px solid var(--border); display:none; }
.cat-access-body.open { display:block; }
.content-section { margin-bottom:.75rem; }
.content-section label { font-size:.78rem; font-weight:600; color:var(--muted); display:block; margin-bottom:.4rem; }
.content-pills { display:flex; flex-wrap:wrap; gap:.35rem; }
.pill-check {
  display:inline-flex; align-items:center; gap:.3rem;
  padding:.25rem .6rem; border-radius:6px; font-size:.78rem;
  background:var(--surface2); border:1px solid var(--border);
  cursor:pointer; transition:background .1s, border .1s;
}
.pill-check:has(input:checked) { background:rgba(139,92,246,.15); border-color:var(--accent); color:var(--accent); }
.pill-check input { display:none; }

/* ─── Vis section ─────────────────────────────────────────────────── */
.vis-section { border:1px solid var(--border); border-radius:10px; padding:.85rem 1rem; margin-bottom:.75rem; }
.vis-section h5 { font-size:.875rem; font-weight:600; margin-bottom:.75rem; }

/* ─── Divider ─────────────────────────────────────────────────────── */
.divider { border-top:1px solid var(--border); margin:1rem 0; }

/* ─── Toast ───────────────────────────────────────────────────────── */
#toast-wrap { position:fixed; bottom:1.5rem; right:1.5rem; z-index:300; display:flex; flex-direction:column; gap:.5rem; }
.toast {
  padding:.65rem 1rem; border-radius:9px; font-size:.825rem; font-weight:500;
  box-shadow:0 4px 20px rgba(0,0,0,.3); animation:toast-in .2s ease-out; min-width:220px;
  display:flex; align-items:center; gap:.5rem;
}
@keyframes toast-in { from { opacity:0; transform:translateX(20px); } to { opacity:1; transform:none; } }
.toast-ok   { background:#134e3a; color:#6ee7b7; border:1px solid #065f46; }
.toast-err  { background:#4c0519; color:#fda4af; border:1px solid #881337; }
.toast-info { background:#0c2a4a; color:#7dd3fc; border:1px solid #075985; }

/* ─── Theme toggle ────────────────────────────────────────────────── */
#theme-btn { font-size:1.1rem; }
</style>
</head>
<body>

<!-- ══════════════════ LOGIN ══════════════════════════════════════════ -->
<div id="login-page">
  <div class="login-card">
    <h2><span class="logo">★</span> Anime Sama Admin</h2>
    <div id="login-err" class="alert alert-danger" style="display:none"></div>
    <div class="form-group">
      <label>Nom d'utilisateur</label>
      <input id="l-user" class="form-control" placeholder="admin" autocomplete="username">
    </div>
    <div class="form-group">
      <label>Mot de passe</label>
      <input id="l-pass" class="form-control" type="password" autocomplete="current-password">
    </div>
    <button class="btn btn-primary" style="width:100%;justify-content:center;padding:.6rem" onclick="doLogin()">
      Connexion
    </button>
  </div>
</div>

<!-- ══════════════════ SHELL ══════════════════════════════════════════ -->
<div id="shell" style="display:none">
  <!-- Sidebar -->
  <aside id="sidebar">
    <div class="sb-brand">
      <div class="title">★ Anime Sama</div>
      <div class="sub">Administration</div>
    </div>
    <nav class="sb-nav">
      <div class="nav-item active" data-tab="users" onclick="switchTab(this)">
        <span class="icon">👥</span> Utilisateurs
      </div>
      <div class="nav-item" data-tab="catalogues" onclick="switchTab(this)">
        <span class="icon">📚</span> Catalogues
      </div>
    </nav>
    <div class="sb-footer">
      <div class="me" id="me-label"></div>
      <button class="btn btn-secondary btn-sm" style="width:100%;justify-content:center;margin-bottom:.4rem"
              id="theme-btn" onclick="toggleTheme()">🌙 Thème clair</button>
      <button class="btn btn-ghost btn-sm" style="width:100%;justify-content:center" onclick="logout()">
        ↩ Déconnexion
      </button>
    </div>
  </aside>

  <!-- Main -->
  <div id="main">
    <div id="topbar">
      <h1 id="topbar-title">Utilisateurs</h1>
      <div class="topbar-actions" id="topbar-actions"></div>
    </div>
    <div id="content">

      <!-- ── Tab : Utilisateurs ───────────────────────────────────── -->
      <div id="tab-users">
        <div class="filter-bar">
          <input id="user-q" placeholder="🔍  Rechercher un utilisateur…" oninput="filterUsers()">
          <select onchange="filterUsers()" id="user-role-filter">
            <option value="">Tous les rôles</option>
            <option value="admin">Admin</option>
            <option value="user">Utilisateur</option>
          </select>
        </div>
        <div class="data-table-wrap">
          <table class="data-table">
            <thead><tr>
              <th>Utilisateur</th>
              <th>Rôle</th>
              <th>Statut</th>
              <th>Permissions</th>
              <th>Accès catalogues</th>
              <th>Actions</th>
            </tr></thead>
            <tbody id="users-body">
              <tr><td colspan="6"><div class="empty-state"><div class="icon">⏳</div>Chargement…</div></td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ── Tab : Catalogues ─────────────────────────────────────── -->
      <div id="tab-catalogues" style="display:none">
        <div class="filter-bar">
          <input id="cat-q" placeholder="🔍  Rechercher un catalogue…" oninput="filterCatalogues()">
          <select id="cat-vis" onchange="filterCatalogues()">
            <option value="">Toute visibilité</option>
            <option value="public">Public</option>
            <option value="prive">Privé</option>
            <option value="partiel">Partiel</option>
          </select>
          <select id="cat-genre" onchange="filterCatalogues()">
            <option value="">Tous les genres</option>
          </select>
        </div>
        <div class="data-table-wrap">
          <table class="data-table">
            <thead><tr>
              <th>Catalogue</th>
              <th>Type</th>
              <th>Contenu</th>
              <th>Genres</th>
              <th>Visibilité</th>
              <th>Actions</th>
            </tr></thead>
            <tbody id="cats-body">
              <tr><td colspan="6"><div class="empty-state"><div class="icon">⏳</div>Chargement…</div></td></tr>
            </tbody>
          </table>
        </div>
      </div>

    </div><!-- /content -->
  </div><!-- /main -->
</div><!-- /shell -->

<!-- ══════════════════ MODALS ══════════════════════════════════════════ -->

<!-- Modal : Éditer utilisateur -->
<div class="modal-backdrop" id="modal-user" style="display:none" onclick="if(event.target===this)closeModal('modal-user')">
  <div class="modal-box md">
    <div class="modal-head">
      <h3 id="mu-title">Utilisateur</h3>
      <button class="btn btn-ghost btn-icon" onclick="closeModal('modal-user')">✕</button>
    </div>
    <div class="modal-body">
      <div id="mu-err" class="alert alert-danger" style="display:none"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem">
        <div class="form-group">
          <label>Nom d'utilisateur *</label>
          <input id="mu-username" class="form-control" placeholder="naruto">
        </div>
        <div class="form-group">
          <label>Email</label>
          <input id="mu-email" class="form-control" type="email" placeholder="…@example.com">
        </div>
        <div class="form-group">
          <label id="mu-pass-label">Mot de passe *</label>
          <input id="mu-password" class="form-control" type="password">
        </div>
        <div class="form-group">
          <label>Rôle</label>
          <select id="mu-role" class="form-select">
            <option value="user">Utilisateur</option>
            <option value="admin">Administrateur</option>
          </select>
        </div>
      </div>
      <div class="form-check" style="margin-bottom:1rem">
        <input type="checkbox" id="mu-active" checked>
        <label for="mu-active">Compte actif</label>
      </div>
      <div class="divider"></div>
      <p style="font-size:.8rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.6rem">
        Permissions opérationnelles
      </p>
      <div style="display:flex;gap:1.25rem;flex-wrap:wrap">
        <label class="form-check"><input type="checkbox" id="mu-sync"> Synchronisation</label>
        <label class="form-check"><input type="checkbox" id="mu-delete"> Suppression</label>
        <label class="form-check"><input type="checkbox" id="mu-refresh"> Rafraîchissement</label>
      </div>
    </div>
    <div class="modal-foot">
      <button class="btn btn-secondary" onclick="closeModal('modal-user')">Annuler</button>
      <button class="btn btn-primary" onclick="saveUser()">Enregistrer</button>
    </div>
  </div>
</div>

<!-- Modal : Accès catalogues d'un utilisateur -->
<div class="modal-backdrop" id="modal-access" style="display:none" onclick="if(event.target===this)closeModal('modal-access')">
  <div class="modal-box lg">
    <div class="modal-head">
      <h3 id="ma-title">Accès aux catalogues</h3>
      <button class="btn btn-ghost btn-icon" onclick="closeModal('modal-access')">✕</button>
    </div>
    <div class="modal-body">
      <div id="ma-err" class="alert alert-danger" style="display:none"></div>
      <div class="form-check form-switch" style="margin-bottom:1rem">
        <input type="checkbox" id="ma-all-cats" onchange="toggleAllCats()">
        <label for="ma-all-cats" style="font-weight:600">Accès à tous les catalogues</label>
      </div>
      <p style="font-size:.8rem;color:var(--muted);margin-bottom:.75rem">
        Activez les catalogues autorisés. Pour chaque catalogue, vous pouvez restreindre
        l'accès à certaines saisons, films ou scans.
      </p>
      <div id="ma-cats-list"></div>
    </div>
    <div class="modal-foot">
      <button class="btn btn-secondary" onclick="closeModal('modal-access')">Annuler</button>
      <button class="btn btn-primary" onclick="saveAccess()">Enregistrer</button>
    </div>
  </div>
</div>

<!-- Modal : Visibilité catalogue -->
<div class="modal-backdrop" id="modal-vis" style="display:none" onclick="if(event.target===this)closeModal('modal-vis')">
  <div class="modal-box md">
    <div class="modal-head">
      <h3 id="mv-title">Visibilité</h3>
      <button class="btn btn-ghost btn-icon" onclick="closeModal('modal-vis')">✕</button>
    </div>
    <div class="modal-body" id="mv-body"></div>
    <div class="modal-foot">
      <button class="btn btn-secondary" onclick="closeModal('modal-vis')">Annuler</button>
      <button class="btn btn-primary" onclick="saveVisibility()">Enregistrer</button>
    </div>
  </div>
</div>

<!-- Toast container -->
<div id="toast-wrap"></div>

<script>
// ─── Config ─────────────────────────────────────────────────────────────────
const API = '__API_BASE__';

// ─── État ────────────────────────────────────────────────────────────────────
let token = localStorage.getItem('as_admin_token') || '';
let allUsers = [], allCats = [];
let editUsername = null;     // null = création, string = édition
let accessUsername = null;   // utilisateur en cours d'édition des accès
let visSlug = null;          // catalogue en cours de visibilité

// ─── Thème ───────────────────────────────────────────────────────────────────
const html = document.documentElement;
const savedTheme = localStorage.getItem('as_theme') || 'dark';
html.setAttribute('data-theme', savedTheme);
function updateThemeBtn() {
  const dark = html.getAttribute('data-theme') === 'dark';
  document.getElementById('theme-btn').textContent = dark ? '☀️ Thème clair' : '🌙 Thème sombre';
}
function toggleTheme() {
  const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('as_theme', next);
  updateThemeBtn();
}
updateThemeBtn();

// ─── API helper ──────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch(API + path, opts);
  if (r.status === 204) return null;
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw data.detail || JSON.stringify(data);
  return data;
}

// ─── Toast ───────────────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast toast-${type === 'ok' ? 'ok' : type === 'err' ? 'err' : 'info'}`;
  el.innerHTML = `<span>${type === 'ok' ? '✓' : type === 'err' ? '✕' : 'ℹ'}</span> ${msg}`;
  document.getElementById('toast-wrap').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ─── Auth ────────────────────────────────────────────────────────────────────
document.getElementById('l-pass').onkeydown = e => { if (e.key === 'Enter') doLogin(); };

async function doLogin() {
  const err = document.getElementById('login-err');
  err.style.display = 'none';
  try {
    const fd = new URLSearchParams({
      username: document.getElementById('l-user').value.trim(),
      password: document.getElementById('l-pass').value,
    });
    const r    = await fetch(API + '/auth/login', { method: 'POST', body: fd });
    const data = await r.json();
    if (!r.ok) throw data.detail || 'Identifiants incorrects';
    token = data.access_token;
    localStorage.setItem('as_admin_token', token);
    await initApp();
  } catch (e) {
    err.textContent = typeof e === 'string' ? e : 'Identifiants incorrects';
    err.style.display = 'block';
  }
}

function logout() {
  localStorage.removeItem('as_admin_token');
  token = '';
  document.getElementById('login-page').style.display = 'flex';
  document.getElementById('shell').style.display = 'none';
}

// ─── Init ────────────────────────────────────────────────────────────────────
async function initApp() {
  try {
    const me = await api('GET', '/auth/me');
    if (me.role !== 'admin') { toast('Réservé aux administrateurs', 'err'); logout(); return; }
    document.getElementById('me-label').textContent = `@ ${me.username}`;
    document.getElementById('login-page').style.display = 'none';
    document.getElementById('shell').style.display = 'flex';
    await Promise.all([loadUsers(), loadCatalogues()]);
  } catch (e) { logout(); }
}

if (token) initApp();

// ─── Tabs ────────────────────────────────────────────────────────────────────
const TAB_TITLES   = { users: 'Utilisateurs', catalogues: 'Catalogues' };
const TAB_ACTIONS  = {
  users:      () => `<button class="btn btn-primary" onclick="openCreateUser()">+ Ajouter</button>`,
  catalogues: () => '',
};

function switchTab(el) {
  const tab = el.dataset.tab;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('tab-users').style.display       = tab === 'users'      ? '' : 'none';
  document.getElementById('tab-catalogues').style.display  = tab === 'catalogues' ? '' : 'none';
  document.getElementById('topbar-title').textContent      = TAB_TITLES[tab] || tab;
  document.getElementById('topbar-actions').innerHTML      = TAB_ACTIONS[tab]?.() || '';
}
// Init topbar
document.getElementById('topbar-actions').innerHTML = TAB_ACTIONS.users();

// ─── USERS ───────────────────────────────────────────────────────────────────
async function loadUsers() {
  allUsers = await api('GET', '/auth/users');
  renderUsers(allUsers);
}

function filterUsers() {
  const q    = document.getElementById('user-q').value.toLowerCase();
  const role = document.getElementById('user-role-filter').value;
  renderUsers(allUsers.filter(u =>
    (!q    || u.username.toLowerCase().includes(q) || (u.email || '').toLowerCase().includes(q)) &&
    (!role || u.role === role)
  ));
}

function renderUsers(users) {
  const tbody = document.getElementById('users-body');
  if (!users.length) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="icon">👤</div>Aucun utilisateur trouvé</div></td></tr>`;
    return;
  }
  tbody.innerHTML = users.map(u => {
    const perms = u.permissions || {};
    const cats  = perms.allowed_catalogues || [];
    const initials = u.username.slice(0, 2).toUpperCase();
    return `<tr>
      <td>
        <div style="display:flex;align-items:center;gap:.6rem">
          <div class="avatar">${initials}</div>
          <div>
            <div style="font-weight:600">${esc(u.username)}</div>
            ${u.email ? `<div style="font-size:.75rem;color:var(--muted)">${esc(u.email)}</div>` : ''}
          </div>
        </div>
      </td>
      <td>
        <span class="badge ${u.role === 'admin' ? 'badge-accent' : 'badge-muted'}">
          ${u.role}
        </span>
      </td>
      <td><span class="badge ${u.is_active ? 'badge-ok' : 'badge-danger'}">${u.is_active ? 'Actif' : 'Inactif'}</span></td>
      <td>
        <div style="display:flex;gap:.25rem;flex-wrap:wrap">
          <span class="perm-chip ${perms.can_sync    ? 'on' : 'off'}">⟳ Sync</span>
          <span class="perm-chip ${perms.can_delete  ? 'on' : 'off'}">🗑 Suppr</span>
          <span class="perm-chip ${perms.can_refresh ? 'on' : 'off'}">↺ Refresh</span>
        </div>
      </td>
      <td>
        ${cats.length === 0
          ? '<span class="badge badge-info">Tous</span>'
          : cats.slice(0,3).map(c => `<span class="tag">${esc(c)}</span>`).join('') +
            (cats.length > 3 ? `<span class="tag">+${cats.length - 3}</span>` : '')
        }
      </td>
      <td>
        <div class="actions">
          <button class="btn btn-secondary btn-icon btn-sm" title="Modifier" onclick="openEditUser('${esc(u.username)}')">✏️</button>
          <button class="btn btn-secondary btn-icon btn-sm" title="Accès catalogues" onclick="openAccess('${esc(u.username)}')">🔑</button>
          <button class="btn btn-danger btn-icon btn-sm" title="Supprimer" onclick="deleteUser('${esc(u.username)}')">🗑</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

// ── Ouvrir modal utilisateur ──
function openCreateUser() {
  editUsername = null;
  document.getElementById('mu-title').textContent = 'Nouvel utilisateur';
  document.getElementById('mu-pass-label').textContent = 'Mot de passe *';
  document.getElementById('mu-username').value  = '';
  document.getElementById('mu-username').disabled = false;
  document.getElementById('mu-email').value     = '';
  document.getElementById('mu-password').value  = '';
  document.getElementById('mu-role').value      = 'user';
  document.getElementById('mu-active').checked  = true;
  document.getElementById('mu-sync').checked    = false;
  document.getElementById('mu-delete').checked  = false;
  document.getElementById('mu-refresh').checked = false;
  document.getElementById('mu-err').style.display = 'none';
  openModal('modal-user');
}

function openEditUser(username) {
  editUsername = username;
  const u = allUsers.find(x => x.username === username);
  document.getElementById('mu-title').textContent = `Modifier — ${username}`;
  document.getElementById('mu-pass-label').textContent = 'Mot de passe (vide = inchangé)';
  document.getElementById('mu-username').value    = u.username;
  document.getElementById('mu-username').disabled = true;
  document.getElementById('mu-email').value       = u.email || '';
  document.getElementById('mu-password').value    = '';
  document.getElementById('mu-role').value        = u.role;
  document.getElementById('mu-active').checked    = u.is_active;
  const p = u.permissions || {};
  document.getElementById('mu-sync').checked    = !!p.can_sync;
  document.getElementById('mu-delete').checked  = !!p.can_delete;
  document.getElementById('mu-refresh').checked = !!p.can_refresh;
  document.getElementById('mu-err').style.display = 'none';
  openModal('modal-user');
}

async function saveUser() {
  const errEl = document.getElementById('mu-err');
  errEl.style.display = 'none';
  try {
    const perms = {
      can_sync:    document.getElementById('mu-sync').checked,
      can_delete:  document.getElementById('mu-delete').checked,
      can_refresh: document.getElementById('mu-refresh').checked,
    };
    if (editUsername) {
      // Préserver les accès catalogues existants
      const existing = allUsers.find(u => u.username === editUsername);
      const existingPerms = existing?.permissions || {};
      perms.allowed_catalogues = existingPerms.allowed_catalogues || [];
      perms.catalogue_content  = existingPerms.catalogue_content  || {};
      const body = {
        is_active:   document.getElementById('mu-active').checked,
        role:        document.getElementById('mu-role').value,
        permissions: perms,
      };
      const email = document.getElementById('mu-email').value;
      if (email) body.email = email;
      const pass = document.getElementById('mu-password').value;
      if (pass) body.password = pass;
      await api('PUT', `/auth/users/${editUsername}`, body);
      toast('Utilisateur mis à jour', 'ok');
    } else {
      const pass = document.getElementById('mu-password').value;
      if (!pass) throw 'Le mot de passe est requis';
      perms.allowed_catalogues = [];
      perms.catalogue_content  = {};
      await api('POST', '/auth/register', {
        username:    document.getElementById('mu-username').value.trim(),
        password:    pass,
        email:       document.getElementById('mu-email').value || null,
        role:        document.getElementById('mu-role').value,
        permissions: perms,
      });
      toast('Utilisateur créé', 'ok');
    }
    closeModal('modal-user');
    await loadUsers();
  } catch (e) {
    errEl.textContent = typeof e === 'string' ? e : JSON.stringify(e);
    errEl.style.display = 'block';
  }
}

async function deleteUser(username) {
  if (!confirm(`Supprimer « ${username} » ? Cette action est irréversible.`)) return;
  try {
    await api('DELETE', `/auth/users/${username}`);
    toast(`${username} supprimé`, 'ok');
    await loadUsers();
  } catch (e) { toast(String(e), 'err'); }
}

// ─── ACCÈS CATALOGUES (modal-access) ─────────────────────────────────────────
function openAccess(username) {
  accessUsername = username;
  const u = allUsers.find(x => x.username === username);
  document.getElementById('ma-title').textContent = `Accès aux catalogues — ${username}`;
  document.getElementById('ma-err').style.display = 'none';

  const perms     = u?.permissions || {};
  const allowed   = perms.allowed_catalogues || [];
  const isAll     = allowed.length === 0;
  const content   = perms.catalogue_content  || {};

  document.getElementById('ma-all-cats').checked = isAll;
  renderAccessList(allowed, content);
  openModal('modal-access');
}

function toggleAllCats() {
  const isAll = document.getElementById('ma-all-cats').checked;
  document.getElementById('ma-cats-list').style.display = isAll ? 'none' : '';
}

function renderAccessList(allowedCats, contentAccess) {
  const list  = document.getElementById('ma-cats-list');
  const isAll = document.getElementById('ma-all-cats').checked;
  list.style.display = isAll ? 'none' : '';

  list.innerHTML = allCats.map(cat => {
    const enabled  = allowedCats.includes(cat.slug);
    const catAccess = contentAccess[cat.slug] || {};
    return `<div class="cat-access-row">
      <div class="cat-access-head" onclick="toggleCatRow('${cat.slug}')">
        <label class="form-switch" onclick="event.stopPropagation()">
          <input type="checkbox" id="ca-${cat.slug}" ${enabled ? 'checked' : ''}
                 onchange="onCatToggle('${cat.slug}')">
        </label>
        <span style="font-weight:600;font-size:.875rem">${esc(cat.nom)}</span>
        <span class="badge badge-muted" style="margin-left:auto">${cat.slug}</span>
        <span style="color:var(--muted);font-size:.85rem">▾</span>
      </div>
      <div class="cat-access-body ${enabled ? 'open' : ''}" id="cab-${cat.slug}">
        ${renderContentRestrictions(cat, catAccess)}
      </div>
    </div>`;
  }).join('');
}

function onCatToggle(slug) {
  const checked = document.getElementById('ca-' + slug).checked;
  const body    = document.getElementById('cab-' + slug);
  if (checked) body.classList.add('open'); else body.classList.remove('open');
}

function toggleCatRow(slug) {
  document.getElementById('cab-' + slug).classList.toggle('open');
}

function renderContentRestrictions(cat, access) {
  const sections = [
    { key: 'saisons', label: '🎬 Saisons', items: cat.saisons },
    { key: 'films',   label: '🎞 Films',   items: cat.films   },
    { key: 'scans',   label: '📖 Scans',   items: cat.scans   },
  ].filter(s => s.items && s.items.length);

  if (!sections.length) return '<p style="color:var(--muted);font-size:.825rem;margin:0">Aucun contenu dans ce catalogue.</p>';

  return sections.map(s => {
    const allowed = access[s.key] || [];
    const isAll   = allowed.length === 0;
    return `<div class="content-section">
      <label>${s.label}</label>
      <div class="content-pills">
        <label class="pill-check">
          <input type="checkbox" class="cr-all" data-cat="${cat.slug}" data-type="${s.key}"
                 ${isAll ? 'checked' : ''} onchange="onAllCheck(this)">
          ✓ Tous
        </label>
        ${s.items.map(item => `
          <label class="pill-check">
            <input type="checkbox" class="cr-item" data-cat="${cat.slug}" data-type="${s.key}"
                   value="${esc(item.slug)}"
                   ${(isAll || allowed.includes(item.slug)) ? 'checked' : ''}>
            ${esc(item.nom || item.slug)}${item.lang ? ` <span style="opacity:.6;font-size:.7rem">(${item.lang})</span>` : ''}
          </label>`).join('')}
      </div>
    </div>`;
  }).join('');
}

function onAllCheck(cb) {
  const cat  = cb.dataset.cat;
  const type = cb.dataset.type;
  const items = document.querySelectorAll(`.cr-item[data-cat="${cat}"][data-type="${type}"]`);
  items.forEach(i => i.checked = cb.checked);
}

async function saveAccess() {
  const errEl = document.getElementById('ma-err');
  errEl.style.display = 'none';
  try {
    const u          = allUsers.find(x => x.username === accessUsername);
    const existPerms = u?.permissions || {};
    const isAll      = document.getElementById('ma-all-cats').checked;

    let allowedCats = [];
    let catContent  = {};

    if (!isAll) {
      allCats.forEach(cat => {
        const enabled = document.getElementById('ca-' + cat.slug)?.checked;
        if (!enabled) return;
        allowedCats.push(cat.slug);

        const types = ['saisons','films','scans'];
        catContent[cat.slug] = {};
        types.forEach(type => {
          const allCb = document.querySelector(`.cr-all[data-cat="${cat.slug}"][data-type="${type}"]`);
          if (!allCb) { catContent[cat.slug][type] = []; return; }
          if (allCb.checked) {
            catContent[cat.slug][type] = [];
          } else {
            catContent[cat.slug][type] = [...document.querySelectorAll(
              `.cr-item[data-cat="${cat.slug}"][data-type="${type}"]:checked`
            )].map(x => x.value);
          }
        });
      });
    }

    const perms = {
      ...existPerms,
      allowed_catalogues: allowedCats,
      catalogue_content:  catContent,
    };
    await api('PUT', `/auth/users/${accessUsername}`, { permissions: perms });
    toast('Accès mis à jour', 'ok');
    closeModal('modal-access');
    await loadUsers();
  } catch (e) {
    errEl.textContent = typeof e === 'string' ? e : JSON.stringify(e);
    errEl.style.display = 'block';
  }
}

// ─── CATALOGUES ───────────────────────────────────────────────────────────────
async function loadCatalogues() {
  allCats = await api('GET', '/admin/api/catalogues');
  // Alimenter le filtre genre
  const genres = [...new Set(allCats.flatMap(c => c.genres || []))].sort();
  const sel = document.getElementById('cat-genre');
  genres.forEach(g => {
    const o = document.createElement('option');
    o.value = g; o.textContent = g;
    sel.appendChild(o);
  });
  filterCatalogues();
}

function catVisClass(cat) {
  const v = cat.visibility || {};
  if (!v.is_public) return 'prive';
  const hasRestriction = [v.public_saisons, v.public_films, v.public_scans].some(l => l?.length);
  return hasRestriction ? 'partiel' : 'public';
}

function filterCatalogues() {
  const q     = document.getElementById('cat-q').value.toLowerCase();
  const vis   = document.getElementById('cat-vis').value;
  const genre = document.getElementById('cat-genre').value;
  const filtered = allCats.filter(c =>
    (!q     || c.nom.toLowerCase().includes(q) || c.slug.includes(q)) &&
    (!vis   || catVisClass(c) === vis) &&
    (!genre || (c.genres || []).includes(genre))
  );
  renderCatalogues(filtered);
}

function renderCatalogues(cats) {
  const tbody = document.getElementById('cats-body');
  if (!cats.length) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><div class="icon">📚</div>Aucun catalogue trouvé</div></td></tr>`;
    return;
  }
  tbody.innerHTML = cats.map(cat => {
    const visClass = catVisClass(cat);
    const visLabel = { public:'Public', prive:'Privé', partiel:'Partiel' }[visClass];
    const visBadge = { public:'badge-ok', prive:'badge-danger', partiel:'badge-warn' }[visClass];
    const genres   = (cat.genres || []).slice(0,3);
    const moreG    = (cat.genres || []).length - genres.length;
    const typeMap  = { anime:'🎬 Anime', scan:'📖 Scan', film:'🎞 Film', autre:'📦 Autre' };
    return `<tr>
      <td>
        <div style="font-weight:600">${esc(cat.nom)}</div>
        <div style="font-size:.75rem;color:var(--muted)">${esc(cat.slug)}</div>
      </td>
      <td><span class="badge badge-muted">${typeMap[cat.type_contenu] || cat.type_contenu}</span></td>
      <td style="font-size:.8rem;color:var(--text2)">
        ${cat.saisons.length ? `<span>${cat.saisons.length} saison${cat.saisons.length>1?'s':''}</span>` : ''}
        ${cat.films.length   ? `<span style="margin-left:.4rem">${cat.films.length} film${cat.films.length>1?'s':''}</span>` : ''}
        ${cat.scans.length   ? `<span style="margin-left:.4rem">${cat.scans.length} scan${cat.scans.length>1?'s':''}</span>` : ''}
      </td>
      <td>
        ${genres.map(g => `<span class="tag">${esc(g)}</span>`).join('')}
        ${moreG > 0 ? `<span class="tag">+${moreG}</span>` : ''}
      </td>
      <td><span class="badge ${visBadge}">${visLabel}</span></td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="openVisibility('${esc(cat.slug)}')">
          ⚙ Visibilité
        </button>
      </td>
    </tr>`;
  }).join('');
}

// ─── VISIBILITÉ ───────────────────────────────────────────────────────────────
function openVisibility(slug) {
  visSlug  = slug;
  const cat = allCats.find(c => c.slug === slug);
  const v   = cat.visibility || { is_public:true, public_saisons:[], public_films:[], public_scans:[] };
  document.getElementById('mv-title').textContent = `Visibilité — ${cat.nom}`;

  const contentSection = (key, label, items) => {
    if (!items?.length) return '';
    const allowed = v['public_' + key] || [];
    const isAll   = allowed.length === 0;
    return `<div class="content-section" id="vis-sec-${key}">
      <label>${label}</label>
      <div class="content-pills">
        <label class="pill-check">
          <input type="checkbox" id="vis-all-${key}" ${isAll ? 'checked' : ''}
                 onchange="onVisAllCheck('${key}')"> ✓ Tous
        </label>
        ${items.map(item => `
          <label class="pill-check">
            <input type="checkbox" class="vis-item" data-type="${key}"
                   value="${esc(item.slug)}" ${(isAll || allowed.includes(item.slug)) ? 'checked' : ''}>
            ${esc(item.nom || item.slug)}${item.lang ? ` <span style="opacity:.6;font-size:.7rem">(${item.lang})</span>` : ''}
          </label>`).join('')}
      </div>
    </div>`;
  };

  document.getElementById('mv-body').innerHTML = `
    <div class="vis-section">
      <label class="form-switch">
        <input type="checkbox" id="vis-public" ${v.is_public !== false ? 'checked' : ''}
               onchange="document.getElementById('vis-content').style.display=this.checked?'':'none'">
        <span style="font-weight:600">Catalogue accessible publiquement</span>
      </label>
      <p style="font-size:.8rem;color:var(--muted);margin:.4rem 0 0 2.6rem">
        Si désactivé, seuls les utilisateurs authentifiés et autorisés verront ce catalogue.
      </p>
    </div>
    <div id="vis-content" ${v.is_public === false ? 'style="display:none"' : ''}>
      <p style="font-size:.8rem;color:var(--muted);margin-bottom:.75rem">
        Sélectionnez le contenu visible sans authentification (« Tous » = tout visible).
      </p>
      ${contentSection('saisons', '🎬 Saisons', cat.saisons)}
      ${contentSection('films',   '🎞  Films',  cat.films)}
      ${contentSection('scans',   '📖 Scans',  cat.scans)}
    </div>
  `;
  openModal('modal-vis');
}

function onVisAllCheck(type) {
  const allChecked = document.getElementById('vis-all-' + type).checked;
  document.querySelectorAll(`.vis-item[data-type="${type}"]`).forEach(i => i.checked = allChecked);
}

async function saveVisibility() {
  const isPublic = document.getElementById('vis-public').checked;
  const getItems = type => {
    if (!isPublic) return [];
    const allCb = document.getElementById('vis-all-' + type);
    if (!allCb || allCb.checked) return [];
    return [...document.querySelectorAll(`.vis-item[data-type="${type}"]:checked`)].map(x => x.value);
  };
  try {
    await api('PUT', `/admin/api/catalogues/${visSlug}/visibility`, {
      is_public:      isPublic,
      public_saisons: getItems('saisons'),
      public_films:   getItems('films'),
      public_scans:   getItems('scans'),
    });
    toast('Visibilité mise à jour', 'ok');
    closeModal('modal-vis');
    await loadCatalogues();
  } catch (e) { toast(String(e), 'err'); }
}

// ─── Modals helpers ───────────────────────────────────────────────────────────
function openModal(id)  { document.getElementById(id).style.display = 'flex'; }
function closeModal(id) { document.getElementById(id).style.display = 'none';  }

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') ['modal-user','modal-access','modal-vis'].forEach(closeModal);
});

// ─── Util ─────────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def admin_ui():
    return HTMLResponse(_HTML.replace("__API_BASE__", API_BASE))


if __name__ == "__main__":
    print(f"  Admin UI  : http://localhost:{ADMIN_PORT}")
    print(f"  API cible : {API_BASE}")
    uvicorn.run("admin_main:app", host="0.0.0.0", port=ADMIN_PORT, reload=True)
