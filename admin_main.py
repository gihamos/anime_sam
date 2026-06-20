"""
Serveur d'administration autonome (port 8001 par défaut).

  python admin_main.py
  API_BASE=http://localhost:8000 ADMIN_PORT=8001 python admin_main.py
"""
import os, uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

API_BASE   = os.getenv("API_BASE",   "http://localhost:8000")
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8001"))

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_HTML = r"""<!DOCTYPE html>
<html lang="fr" data-theme="dark">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anime Sama · Admin</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<style>
:root{
  --bg:#0f172a;--sur:#1e293b;--sur2:#263043;--surh:#2d3f56;
  --bdr:#334155;--tx:#f1f5f9;--tx2:#cbd5e1;--mu:#94a3b8;
  --ac:#8b5cf6;--ach:#7c3aed;
  --ok:#10b981;--wa:#f59e0b;--er:#f43f5e;--info:#38bdf8;
  --sbw:230px;--tbh:54px;
}
[data-theme="light"]{
  --bg:#f1f5f9;--sur:#fff;--sur2:#f8fafc;--surh:#e2e8f0;
  --bdr:#cbd5e1;--tx:#0f172a;--tx2:#1e293b;--mu:#64748b;
  --ac:#7c3aed;--ach:#6d28d9;
  --ok:#059669;--wa:#d97706;--er:#dc2626;--info:#0284c7;
}
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font-family:system-ui,sans-serif}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-thumb{background:var(--bdr);border-radius:3px}

/* Layout */
#shell{display:flex;height:100vh;overflow:hidden}
#sidebar{width:var(--sbw);flex-shrink:0;background:var(--sur);border-right:1px solid var(--bdr);display:flex;flex-direction:column}
#main{flex:1;display:flex;flex-direction:column;min-width:0;overflow:hidden}
#topbar{height:var(--tbh);flex-shrink:0;background:var(--sur);border-bottom:1px solid var(--bdr);display:flex;align-items:center;padding:0 1.5rem;gap:.75rem}
#content{flex:1;overflow-y:auto;padding:1.25rem 1.75rem;display:flex;flex-direction:column}

/* Sidebar */
.sb-brand{padding:.85rem 1rem .65rem;border-bottom:1px solid var(--bdr)}
.sb-brand .t{font-size:.9rem;font-weight:700;color:var(--ac)}.sb-brand .s{font-size:.7rem;color:var(--mu)}
.sb-nav{flex:1;padding:.6rem .4rem;overflow-y:auto}
.ni{display:flex;align-items:center;gap:.55rem;padding:.45rem .7rem;border-radius:7px;cursor:pointer;color:var(--mu);font-size:.85rem;font-weight:500;transition:background .12s,color .12s;user-select:none}
.ni:hover{background:var(--surh);color:var(--tx2)}.ni.active{background:rgba(139,92,246,.14);color:var(--ac)}
.sb-foot{padding:.65rem .9rem;border-top:1px solid var(--bdr);font-size:.76rem;color:var(--mu)}
.sb-foot .me{margin-bottom:.35rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* Topbar */
#topbar h1{font-size:.95rem;font-weight:600;margin:0;flex:1}
#sync-badge{display:none;background:rgba(56,189,248,.14);color:var(--info);border:1px solid rgba(56,189,248,.25);border-radius:999px;padding:.18rem .6rem;font-size:.72rem;font-weight:600;cursor:pointer;white-space:nowrap}

/* Buttons */
.btn{border:none;border-radius:7px;font-size:.8rem;font-weight:500;padding:.38rem .8rem;cursor:pointer;transition:background .12s,opacity .12s;display:inline-flex;align-items:center;gap:.35rem;line-height:1.4}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-primary{background:var(--ac);color:#fff}.btn-primary:hover{background:var(--ach)}
.btn-secondary{background:var(--sur2);color:var(--tx2);border:1px solid var(--bdr)}.btn-secondary:hover{background:var(--surh)}
.btn-danger{background:rgba(244,63,94,.1);color:var(--er);border:1px solid rgba(244,63,94,.2)}.btn-danger:hover{background:rgba(244,63,94,.2)}
.btn-warn{background:rgba(245,158,11,.1);color:var(--wa);border:1px solid rgba(245,158,11,.2)}.btn-warn:hover{background:rgba(245,158,11,.2)}
.btn-ok{background:rgba(16,185,129,.1);color:var(--ok);border:1px solid rgba(16,185,129,.2)}.btn-ok:hover{background:rgba(16,185,129,.2)}
.btn-info{background:rgba(56,189,248,.1);color:var(--info);border:1px solid rgba(56,189,248,.2)}.btn-info:hover{background:rgba(56,189,248,.2)}
.btn-ghost{background:transparent;color:var(--mu);padding:.3rem .45rem}.btn-ghost:hover{background:var(--sur2);color:var(--tx)}
.btn-sm{font-size:.75rem;padding:.28rem .55rem}.btn-icon{padding:.3rem .4rem;border-radius:6px}

/* Filter bar */
.fbar{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;background:var(--sur);border:1px solid var(--bdr);border-radius:9px;padding:.55rem .85rem;margin-bottom:.85rem}
.fbar input,.fbar select{background:var(--sur2);border:1px solid var(--bdr);color:var(--tx);border-radius:6px;padding:.3rem .65rem;font-size:.8rem;outline:none;transition:border .12s}
.fbar input:focus,.fbar select:focus{border-color:var(--ac)}
.fbar input{flex:1;min-width:150px}.fbar select{min-width:120px}

/* Table */
.dtw{background:var(--sur);border:1px solid var(--bdr);border-radius:11px;overflow:hidden}
.dt{width:100%;border-collapse:collapse}
.dt thead tr{background:var(--sur2)}
.dt thead th{padding:.6rem .85rem;font-size:.73rem;font-weight:600;color:var(--mu);text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid var(--bdr);white-space:nowrap}
.dt tbody td{padding:.6rem .85rem;font-size:.82rem;border-bottom:1px solid var(--bdr);vertical-align:middle}
.dt tbody tr:last-child td{border-bottom:none}
.dt tbody tr:hover td{background:var(--surh)}
.actions{display:flex;gap:.3rem;flex-wrap:nowrap}

/* Badge */
.badge{display:inline-block;border-radius:999px;padding:.18rem .55rem;font-size:.7rem;font-weight:600;white-space:nowrap}
.b-ac{background:rgba(139,92,246,.14);color:var(--ac)}.b-ok{background:rgba(16,185,129,.14);color:var(--ok)}
.b-wa{background:rgba(245,158,11,.14);color:var(--wa)}.b-er{background:rgba(244,63,94,.14);color:var(--er)}
.b-info{background:rgba(56,189,248,.14);color:var(--info)}.b-mu{background:var(--sur2);color:var(--mu)}

/* Avatar */
.av{width:30px;height:30px;border-radius:50%;background:rgba(139,92,246,.18);color:var(--ac);font-weight:700;font-size:.72rem;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0}
.avc{width:30px;height:30px;border-radius:50%;background:rgba(56,189,248,.15);color:var(--info);font-weight:700;font-size:.72rem;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0}

/* Perms */
.pc{display:inline-flex;align-items:center;gap:.2rem;padding:.12rem .4rem;border-radius:4px;font-size:.7rem;font-weight:500;background:var(--sur2);color:var(--mu)}
.pc.on{background:rgba(16,185,129,.1);color:var(--ok)}
.tag{display:inline-block;padding:.12rem .45rem;border-radius:4px;font-size:.7rem;background:var(--sur2);color:var(--tx2);margin:1px}

/* Login */
#login-page{position:fixed;inset:0;background:var(--bg);display:flex;align-items:center;justify-content:center;z-index:100}
.lcard{width:370px;background:var(--sur);border:1px solid var(--bdr);border-radius:14px;padding:1.75rem;box-shadow:0 20px 60px rgba(0,0,0,.4)}
.lcard h2{text-align:center;font-size:1.15rem;font-weight:700;margin-bottom:1.4rem}

/* Form */
.fg{margin-bottom:.85rem}
.fg label{display:block;font-size:.78rem;font-weight:500;color:var(--tx2);margin-bottom:.3rem}
.fc,.fs{width:100%;background:var(--sur2);border:1px solid var(--bdr);color:var(--tx);border-radius:7px;padding:.45rem .7rem;font-size:.85rem;outline:none;transition:border .12s}
.fc:focus,.fs:focus{border-color:var(--ac)}.fc::placeholder{color:var(--mu)}
textarea.fc{resize:vertical;min-height:80px;font-family:inherit}
.fcheck{display:flex;align-items:center;gap:.45rem;cursor:pointer}
.fcheck input[type=checkbox]{width:15px;height:15px;border-radius:3px;accent-color:var(--ac);cursor:pointer;flex-shrink:0}
.fsw{display:flex;align-items:center;gap:.55rem;cursor:pointer}
.fsw input[type=checkbox]{width:32px;height:17px;appearance:none;border-radius:999px;background:var(--bdr);cursor:pointer;position:relative;transition:background .2s;flex-shrink:0}
.fsw input:checked{background:var(--ac)}
.fsw input::after{content:'';position:absolute;width:11px;height:11px;background:#fff;border-radius:50%;top:3px;left:3px;transition:left .18s}
.fsw input:checked::after{left:18px}

/* Modal */
.mbk{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:200;display:flex;align-items:center;justify-content:center;padding:1rem}
.mbox{background:var(--sur);border:1px solid var(--bdr);border-radius:13px;width:100%;box-shadow:0 25px 80px rgba(0,0,0,.55);display:flex;flex-direction:column;max-height:90vh;animation:mi .17s ease-out}
@keyframes mi{from{opacity:0;transform:translateY(8px) scale(.97)}to{opacity:1;transform:none}}
.mbox.sm{max-width:480px}.mbox.md{max-width:640px}.mbox.lg{max-width:820px}.mbox.xl{max-width:1000px}
.mhd{display:flex;align-items:center;padding:.9rem 1.1rem;border-bottom:1px solid var(--bdr);gap:.65rem;flex-shrink:0}
.mhd h3{margin:0;font-size:.95rem;font-weight:600;flex:1}
.mbd{padding:1.1rem;overflow-y:auto;flex:1}.mft{display:flex;justify-content:flex-end;gap:.5rem;padding:.85rem 1.1rem;border-top:1px solid var(--bdr);flex-shrink:0;flex-wrap:wrap}

/* Alerts */
.alert{padding:.55rem .8rem;border-radius:7px;font-size:.8rem;margin-bottom:.65rem}
.a-er{background:rgba(244,63,94,.1);color:var(--er);border:1px solid rgba(244,63,94,.2)}
.a-ok{background:rgba(16,185,129,.1);color:var(--ok);border:1px solid rgba(16,185,129,.2)}
.a-wa{background:rgba(245,158,11,.1);color:var(--wa);border:1px solid rgba(245,158,11,.2)}
.a-info{background:rgba(56,189,248,.1);color:var(--info);border:1px solid rgba(56,189,248,.2)}

/* Secret reveal box */
.secret-box{background:var(--bg);border:1px solid var(--bdr);border-radius:8px;padding:.65rem .85rem;font-family:monospace;font-size:.82rem;word-break:break-all;position:relative}
.secret-box .s-label{font-size:.7rem;font-weight:600;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.3rem}
.secret-val{color:var(--ok);font-weight:600}

/* Progress */
.prog-wrap{height:8px;background:var(--bdr);border-radius:4px;overflow:hidden;margin:.55rem 0}
.prog-fill{height:100%;border-radius:4px;transition:width .35s,background .3s;width:0;background:var(--ac)}
.prog-fill.paused{background:var(--wa)}.prog-fill.done{background:var(--ok)}.prog-fill.er{background:var(--er)}.prog-fill.cancelled{background:var(--mu)}

/* Sync */
.sync-ctrl{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;margin:.6rem 0}
.sync-log{background:var(--bg);border:1px solid var(--bdr);border-radius:8px;padding:.6rem .8rem;font-size:.74rem;font-family:monospace;color:var(--tx2);max-height:190px;overflow-y:auto;margin-top:.5rem}
.sl-ok{color:var(--ok)}.sl-skip{color:var(--mu)}.sl-run{color:var(--info)}.sl-er{color:var(--er)}.sl-pause{color:var(--wa)}.sl-cancel{color:var(--er)}

/* Background syncs bar */
#bg-bar{flex-shrink:0;margin-top:auto;border-top:1px solid var(--bdr);padding-top:.65rem;display:none}
#bg-bar .bbt{font-size:.73rem;font-weight:600;color:var(--mu);text-transform:uppercase;letter-spacing:.04em;margin-bottom:.4rem}
.bg-item{display:flex;align-items:center;gap:.55rem;background:var(--sur);border:1px solid var(--bdr);border-radius:8px;padding:.45rem .7rem;margin-bottom:.35rem}
.bg-item .bi-slug{font-weight:600;font-size:.8rem;min-width:100px}
.bg-item .bi-pct{font-size:.75rem;color:var(--mu);min-width:30px;text-align:right}
.bg-item .mini-prog{flex:1;height:5px;background:var(--bdr);border-radius:3px;overflow:hidden;min-width:60px}
.bg-item .mini-fill{height:100%;border-radius:3px;transition:width .3s,background .3s;background:var(--ac)}.bg-item .mini-fill.paused{background:var(--wa)}

/* Cat access */
.car{border:1px solid var(--bdr);border-radius:9px;overflow:hidden;margin-bottom:.4rem}
.cah{display:flex;align-items:center;gap:.65rem;padding:.55rem .8rem;background:var(--sur2);cursor:pointer;user-select:none}
.cah:hover{background:var(--surh)}.cab{padding:.65rem .8rem;border-top:1px solid var(--bdr);display:none}.cab.open{display:block}
.cs label{font-size:.74rem;font-weight:600;color:var(--mu);display:block;margin-bottom:.3rem}
.pills{display:flex;flex-wrap:wrap;gap:.3rem}
.pill{display:inline-flex;align-items:center;gap:.25rem;padding:.2rem .55rem;border-radius:5px;font-size:.74rem;background:var(--sur2);border:1px solid var(--bdr);cursor:pointer;transition:background .1s,border .1s}
.pill:has(input:checked){background:rgba(139,92,246,.14);border-color:var(--ac);color:var(--ac)}
.pill input{display:none}

/* Tags éditables */
.tag-box{display:flex;flex-wrap:wrap;gap:.3rem;align-items:center;background:var(--sur2);border:1px solid var(--bdr);border-radius:7px;padding:.35rem .5rem;min-height:38px}
.tag-box:focus-within{border-color:var(--ac)}
.etag{display:inline-flex;align-items:center;gap:.25rem;background:rgba(139,92,246,.12);color:var(--ac);border-radius:4px;padding:.15rem .45rem;font-size:.75rem}
.etag button{background:none;border:none;color:inherit;cursor:pointer;padding:0;line-height:1;font-size:.8rem}
.tag-input{background:none;border:none;outline:none;color:var(--tx);font-size:.82rem;min-width:80px;flex:1}
.tag-input::placeholder{color:var(--mu)}

/* Content viewer */
.ctabs{display:flex;gap:0;border-bottom:2px solid var(--bdr);margin-bottom:1rem}
.ctab{padding:.45rem 1rem;font-size:.83rem;font-weight:500;cursor:pointer;color:var(--mu);border-bottom:2px solid transparent;margin-bottom:-2px;transition:color .12s,border-color .12s}
.ctab:hover{color:var(--tx2)}.ctab.active{color:var(--ac);border-bottom-color:var(--ac)}
.ctab-content{display:none}.ctab-content.active{display:block}
.citem{border:1px solid var(--bdr);border-radius:9px;margin-bottom:.5rem;overflow:hidden}
.citem-head{display:flex;align-items:center;gap:.6rem;padding:.6rem .85rem;background:var(--sur2);cursor:pointer;user-select:none}
.citem-head:hover{background:var(--surh)}.citem-head .ci-nom{font-weight:600;font-size:.85rem;flex:1}.citem-head .ci-count{font-size:.78rem;color:var(--mu)}
.citem-body{padding:.75rem .85rem;border-top:1px solid var(--bdr);display:none}.citem-body.open{display:block}.citem-body.unsynced{color:var(--mu);font-size:.82rem;text-align:center;padding:1rem}
.ep-grid{display:flex;flex-wrap:wrap;gap:.2rem;margin-top:.35rem}
.ep-chip{display:inline-block;min-width:32px;padding:.15rem .25rem;background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.25);border-radius:4px;font-size:.7rem;text-align:center;color:var(--ok);font-family:monospace}
.ep-chip.chap{background:rgba(139,92,246,.08);border-color:rgba(139,92,246,.25);color:var(--ac)}
.ep-more{display:inline-block;padding:.15rem .5rem;background:var(--sur2);border:1px solid var(--bdr);border-radius:4px;font-size:.7rem;color:var(--mu);cursor:pointer;margin-top:.2rem}
.ep-more:hover{background:var(--surh)}.lecteur-pill{display:inline-flex;align-items:center;gap:.3rem;background:var(--sur2);border:1px solid var(--bdr);border-radius:6px;padding:.2rem .5rem;font-size:.75rem;margin:.15rem}
.ep-chip.playable{cursor:pointer;background:rgba(16,185,129,.18);border-color:rgba(16,185,129,.5)}.ep-chip.playable:hover{background:rgba(16,185,129,.32);transform:scale(1.07)}
.lecteur-pill.playable{cursor:pointer;background:rgba(56,189,248,.1);border-color:rgba(56,189,248,.3);color:var(--info)}.lecteur-pill.playable:hover{background:rgba(56,189,248,.22)}
.btn-danger{background:rgba(244,63,94,.15);color:var(--er);border:1px solid rgba(244,63,94,.35)}.btn-danger:hover{background:rgba(244,63,94,.28);border-color:var(--er)}
#bulk-del-btn{display:none}
/* Player modal */
#m-player .mbox{max-width:960px;height:85vh}
#mp-frame-wrap{flex:1;background:#000;position:relative;min-height:200px}
#mp-iframe{position:absolute;inset:0;width:100%;height:100%;border:none}
#mp-lects{display:flex;gap:.35rem;padding:.5rem .9rem;border-bottom:1px solid var(--bdr);flex-wrap:wrap;align-items:center;flex-shrink:0}
#mp-lects .lbl{font-size:.74rem;color:var(--mu);margin-right:.15rem}

/* Search results */
.sr-item{display:flex;align-items:center;gap:.65rem;padding:.5rem .7rem;border-radius:8px;border:1px solid var(--bdr);background:var(--sur2);margin-bottom:.35rem;cursor:pointer;transition:background .1s,border-color .1s}
.sr-item:hover{background:var(--surh);border-color:var(--ac)}.sr-item.selected{background:rgba(139,92,246,.12);border-color:var(--ac)}
.sr-img{width:38px;height:54px;border-radius:4px;object-fit:cover;flex-shrink:0;background:var(--bdr)}
.sr-nom{font-weight:600;font-size:.85rem;flex:1}.sr-slug{font-size:.73rem;color:var(--mu);font-family:monospace}
.search-sep{text-align:center;font-size:.75rem;color:var(--mu);margin:.75rem 0;position:relative}
.search-sep::before,.search-sep::after{content:'';position:absolute;top:50%;width:40%;height:1px;background:var(--bdr)}
.search-sep::before{left:0}.search-sep::after{right:0}

/* Misc */
.div{border-top:1px solid var(--bdr);margin:.85rem 0}
.empty{text-align:center;padding:2.5rem;color:var(--mu)}.empty .ic{font-size:2rem;margin-bottom:.5rem}
.spinner{display:inline-block;width:16px;height:16px;border:2px solid var(--bdr);border-top-color:var(--ac);border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.mono{font-family:monospace;font-size:.82rem;color:var(--info);background:rgba(56,189,248,.07);padding:.1rem .35rem;border-radius:4px;word-break:break-all}

/* Planning / History */
.section-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:.65rem}
.section-hd h2{font-size:.88rem;font-weight:700;margin:0;color:var(--tx2)}
.htable-wrap{background:var(--sur);border:1px solid var(--bdr);border-radius:11px;overflow:hidden;margin-bottom:1.25rem}
.status-chip{display:inline-flex;align-items:center;gap:.25rem;padding:.18rem .5rem;border-radius:5px;font-size:.72rem;font-weight:600}
.sc-completed{background:rgba(16,185,129,.12);color:var(--ok)}.sc-cancelled{background:var(--sur2);color:var(--mu)}.sc-error{background:rgba(244,63,94,.1);color:var(--er)}.sc-running{background:rgba(56,189,248,.1);color:var(--info)}
.quota-used{font-size:.72rem;color:var(--mu)}.quota-warn{color:var(--wa)!important}

/* Groupes */
.gt-badge{display:inline-flex;align-items:center;gap:.2rem;padding:.18rem .5rem;border-radius:5px;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.03em}
.gt-catalogue{background:rgba(139,92,246,.12);color:var(--ac)}.gt-genre{background:rgba(56,189,248,.12);color:var(--info)}.gt-permission{background:rgba(16,185,129,.12);color:var(--ok)}
.genre-chips{display:flex;flex-wrap:wrap;gap:.3rem;padding:.35rem 0}
.genre-chip{display:inline-flex;align-items:center;gap:.2rem;padding:.2rem .5rem;background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.25);border-radius:5px;font-size:.76rem;color:var(--info)}
.genre-chip button{border:none;background:none;color:inherit;cursor:pointer;padding:0;font-size:.8rem;line-height:1;opacity:.7}.genre-chip button:hover{opacity:1}

/* Groupe modal — recherche catalogue */
.mg-cat-search-wrap{position:relative}
.mg-cat-search-wrap .search-drop{position:absolute;top:calc(100% + 2px);left:0;right:0;background:var(--sur);border:1px solid var(--bdr);border-radius:8px;max-height:190px;overflow-y:auto;z-index:60;box-shadow:0 6px 24px rgba(0,0,0,.25)}
.mg-cat-search-wrap .sd-item{padding:.45rem .75rem;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:.5rem;font-size:.83rem;border-bottom:1px solid var(--bdr)}
.mg-cat-search-wrap .sd-item:last-child{border-bottom:none}.mg-cat-search-wrap .sd-item:hover{background:var(--surh)}
.mg-cat-search-wrap .sd-slug{font-size:.7rem;color:var(--mu);font-family:monospace}
.mg-cat-search-wrap .sd-empty{padding:.6rem .75rem;font-size:.8rem;color:var(--mu);text-align:center}

/* Groupe modal — grille genres */
.genre-grid-wrap{background:var(--sur2);border:1px solid var(--bdr);border-radius:8px;overflow:hidden}
.genre-grid-filter{padding:.4rem .5rem;border-bottom:1px solid var(--bdr)}
.genre-grid-filter input{width:100%;background:transparent;border:none;outline:none;font-size:.82rem;color:var(--tx);padding:.1rem}
.genre-grid{display:flex;flex-wrap:wrap;gap:.3rem;padding:.5rem;max-height:160px;overflow-y:auto}
.gs-chip{padding:.22rem .6rem;border-radius:20px;font-size:.77rem;cursor:pointer;border:1px solid var(--bdr);background:var(--sur);color:var(--tx2);transition:all .1s;user-select:none}
.gs-chip:hover{border-color:var(--info);color:var(--info)}
.gs-chip.on{background:rgba(56,189,248,.15);border-color:var(--info);color:var(--info);font-weight:600}
.genre-grid-sync{display:flex;align-items:center;gap:.5rem;padding:.35rem .5rem;border-top:1px solid var(--bdr);font-size:.75rem;color:var(--mu)}
.genre-grid-sync button{margin-left:auto}

/* OIDC login */
.oidc-sep{display:flex;align-items:center;gap:.5rem;margin:.9rem 0;color:var(--mu);font-size:.78rem}
.oidc-sep::before,.oidc-sep::after{content:'';flex:1;border-top:1px solid var(--bdr)}
.btn-oidc{display:flex;align-items:center;justify-content:center;gap:.5rem;width:100%;padding:.5rem;border:1px solid var(--bdr);border-radius:8px;background:var(--sur2);color:var(--tx);font-size:.85rem;font-weight:500;cursor:pointer;transition:background .12s,border-color .12s;margin-bottom:.4rem;text-decoration:none}
.btn-oidc:hover{background:var(--surh);border-color:var(--ac)}
.oidc-icon{width:18px;height:18px;border-radius:3px}
#oidc-btns{margin-top:0}

/* Planning Sorties */
.ptab-nav{display:flex;gap:0;border-bottom:2px solid var(--bdr);margin-bottom:1rem}
.ptab{padding:.5rem 1.1rem;font-size:.84rem;font-weight:500;cursor:pointer;color:var(--mu);border-bottom:2px solid transparent;margin-bottom:-2px;transition:color .12s,border-color .12s}
.ptab:hover{color:var(--tx2)}.ptab.active{color:var(--ac);border-bottom-color:var(--ac)}
.ptab-content{display:none}.ptab-content.active{display:block}

.week-grid{display:grid;grid-template-columns:repeat(7,minmax(140px,1fr));gap:.55rem;margin-bottom:1rem;overflow-x:auto}
@media(max-width:900px){.week-grid{grid-template-columns:repeat(4,minmax(130px,1fr))}}
.day-col{background:var(--sur);border:1px solid var(--bdr);border-radius:10px;overflow:hidden;min-width:130px}
.day-col.today{border-color:var(--ac);background:rgba(139,92,246,.04)}
.day-hd{padding:.5rem .7rem;border-bottom:1px solid var(--bdr);text-align:center}
.day-hd .dnom{font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--tx2)}
.day-hd .ddate{font-size:.72rem;color:var(--mu)}
.day-col.today .dnom{color:var(--ac)}
.day-animes{padding:.35rem .4rem}
.anime-card{display:flex;align-items:center;gap:.45rem;padding:.35rem .4rem;border-radius:7px;cursor:pointer;transition:background .1s;margin-bottom:.2rem;border:1px solid transparent}
.anime-card:hover{background:var(--surh);border-color:var(--bdr)}
.anime-card.in-db{border-color:rgba(16,185,129,.2);background:rgba(16,185,129,.04)}
.anime-thumb{width:32px;height:44px;border-radius:4px;object-fit:cover;flex-shrink:0;background:var(--sur2)}
.anime-thumb-ph{width:32px;height:44px;border-radius:4px;background:var(--sur2);display:flex;align-items:center;justify-content:center;font-size:.9rem;flex-shrink:0}
.anime-info{min-width:0;flex:1}
.anime-titre{font-size:.75rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--tx)}
.anime-sub{font-size:.68rem;color:var(--mu);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.anime-heure{font-size:.7rem;font-weight:600;color:var(--ac);white-space:nowrap}
.lang-badge{display:inline-block;padding:.08rem .3rem;border-radius:3px;font-size:.63rem;font-weight:700;text-transform:uppercase;letter-spacing:.03em;background:var(--sur2);color:var(--mu);margin-top:.1rem}
.lang-vostfr{background:rgba(56,189,248,.12);color:var(--info)}
.lang-vf{background:rgba(139,92,246,.12);color:var(--ac)}
.anime-actions{display:flex;flex-direction:column;gap:.15rem;flex-shrink:0}
.no-anime{text-align:center;padding:.85rem .4rem;font-size:.75rem;color:var(--mu)}
.planning-legend{display:flex;gap:.85rem;flex-wrap:wrap;align-items:center;font-size:.75rem;color:var(--mu);margin-bottom:.75rem}
.planning-legend span{display:flex;align-items:center;gap:.3rem}

/* Block badge */
.b-block{background:rgba(244,63,94,.12);color:var(--er);border:1px solid rgba(244,63,94,.25)}
.blocked-banner{background:rgba(244,63,94,.07);border:1px solid rgba(244,63,94,.2);border-radius:7px;padding:.5rem .7rem;font-size:.8rem;color:var(--er);margin-bottom:.75rem;display:flex;align-items:center;gap:.5rem}

/* Recherche avancée */
.search-layout{display:grid;grid-template-columns:220px 1fr;gap:1rem;align-items:start}
@media(max-width:820px){.search-layout{grid-template-columns:1fr}}
.search-filters{background:var(--sur);border:1px solid var(--bdr);border-radius:10px;padding:.8rem;position:sticky;top:0}
.sf-section{margin-bottom:.65rem}
.sf-label{display:block;font-size:.72rem;font-weight:700;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.3rem}
.sf-checks{display:flex;flex-direction:column;gap:.2rem}
.search-results-area{min-width:0}
.search-results-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:.75rem}
.src-card{background:var(--sur);border:1px solid var(--bdr);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;transition:border-color .15s,box-shadow .15s}
.src-card:hover{border-color:var(--ac);box-shadow:0 2px 12px rgba(139,92,246,.12)}
.src-card.in-db{border-color:rgba(16,185,129,.4)}
.src-poster{width:100%;aspect-ratio:2/3;object-fit:cover;background:var(--sur2);display:block}
.src-poster-ph{width:100%;aspect-ratio:2/3;display:flex;align-items:center;justify-content:center;font-size:2.2rem;background:var(--sur2);color:var(--mu)}
.src-info{padding:.5rem .55rem;flex:1;display:flex;flex-direction:column;gap:.2rem}
.src-nom{font-size:.79rem;font-weight:600;color:var(--tx);line-height:1.3;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.src-slug{font-size:.68rem;color:var(--mu);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.src-foot{padding:.38rem .55rem;border-top:1px solid var(--bdr);display:flex;align-items:center;justify-content:space-between;gap:.3rem;flex-wrap:wrap}
/* Toasts */
#toasts{position:fixed;bottom:1.25rem;right:1.25rem;z-index:300;display:flex;flex-direction:column;gap:.4rem}
.toast{padding:.6rem .9rem;border-radius:8px;font-size:.8rem;font-weight:500;box-shadow:0 4px 20px rgba(0,0,0,.3);animation:ti .18s ease-out;min-width:210px;display:flex;align-items:center;gap:.45rem}
@keyframes ti{from{opacity:0;transform:translateX(18px)}to{opacity:1;transform:none}}
.t-ok{background:#0d3d2b;color:#6ee7b7;border:1px solid #065f46}
.t-er{background:#3d0d1b;color:#fda4af;border:1px solid #881337}
.t-info{background:#0c2a4a;color:#7dd3fc;border:1px solid #075985}
.t-wa{background:#3d2a00;color:#fde68a;border:1px solid #92400e}
</style>
</head>
<body>

<!-- LOGIN -->
<div id="login-page">
  <div class="lcard">
    <h2>★ Anime Sama Admin</h2>
    <div id="lerr" class="alert a-er" style="display:none"></div>
    <div id="lerr-oidc" class="alert a-er" style="display:none"></div>
    <div class="fg"><label>Nom d'utilisateur</label><input id="lu" class="fc" placeholder="admin" onkeydown="if(event.key==='Enter')document.getElementById('lp').focus()"></div>
    <div class="fg"><label>Mot de passe</label><input id="lp" class="fc" type="password" onkeydown="if(event.key==='Enter')doLogin()"></div>
    <button class="btn btn-primary" style="width:100%;justify-content:center;padding:.55rem" onclick="doLogin()">Connexion</button>
    <div id="oidc-btns" style="display:none">
      <div class="oidc-sep">ou continuer avec</div>
      <div id="oidc-providers-list"></div>
    </div>
  </div>
</div>

<!-- SHELL -->
<div id="shell" style="display:none">
  <aside id="sidebar">
    <div class="sb-brand"><div class="t">★ Anime Sama</div><div class="s">Administration</div></div>
    <nav class="sb-nav">
      <div class="ni active" data-tab="users"     onclick="switchTab(this)"><span>👥</span> Utilisateurs</div>
      <div class="ni"        data-tab="catalogues" onclick="switchTab(this)"><span>📚</span> Catalogues</div>
      <div class="ni"        data-tab="groups"     onclick="switchTab(this)"><span>🏷️</span> Groupes</div>
      <div class="ni"        data-tab="search"     onclick="switchTab(this)"><span>🔍</span> Recherche</div>
      <div class="ni"        data-tab="apps"       onclick="switchTab(this)"><span>🔌</span> Applications</div>
      <div class="ni"        data-tab="planning"   onclick="switchTab(this)"><span>📅</span> Planification</div>
    </nav>
    <div class="sb-foot">
      <div class="me" id="me-lbl"></div>
      <button class="btn btn-secondary btn-sm" style="width:100%;justify-content:center;margin-bottom:.35rem" onclick="toggleTheme()" id="tbtn">☀️ Thème clair</button>
      <button class="btn btn-ghost btn-sm" style="width:100%;justify-content:center" onclick="logout()">↩ Déconnexion</button>
    </div>
  </aside>
  <div id="main">
    <div id="topbar">
      <h1 id="tb-title">Utilisateurs</h1>
      <span id="sync-badge" onclick="goToCatalogues()"></span>
      <div id="tb-actions"></div>
    </div>
    <div id="content">

      <!-- USERS -->
      <div id="tab-users">
        <div class="fbar">
          <input id="uq" placeholder="🔍 Rechercher…" oninput="filterUsers()">
          <select onchange="filterUsers()" id="uf-role">
            <option value="">Tous les rôles</option><option value="admin">Admin</option><option value="user">Utilisateur</option>
          </select>
        </div>
        <div class="dtw"><table class="dt">
          <thead><tr><th>Utilisateur</th><th>Rôle</th><th>Statut</th><th>Permissions</th><th>Accès catalogues</th><th>Actions</th></tr></thead>
          <tbody id="utbody"><tr><td colspan="6"><div class="empty"><div class="ic">⏳</div>Chargement…</div></td></tr></tbody>
        </table></div>
      </div>

      <!-- CATALOGUES -->
      <div id="tab-catalogues" style="display:none">
        <div class="fbar">
          <input id="cq" placeholder="🔍 Rechercher nom ou slug…" oninput="filterCats()">
          <select id="cf-vis" onchange="filterCats()"><option value="">Toute visibilité</option><option value="public">Public</option><option value="prive">Privé</option><option value="partiel">Partiel</option></select>
          <select id="cf-etat" onchange="filterCats()"><option value="">Tout état</option><option value="en_cours">En cours</option><option value="termine">Terminé</option><option value="abandonne">Abandonné</option></select>
          <select id="cf-sync" onchange="filterCats()"><option value="">Toute sync</option><option value="no">Non synchronisé</option><option value="yes">Synchronisé</option></select>
          <select id="cf-genre" onchange="filterCats()"><option value="">Tous les genres</option></select>
          <button id="bulk-del-btn" class="btn btn-danger btn-sm" onclick="openDeleteSelected()">🗑 Supprimer la sélection (<span id="bulk-del-count">0</span>)</button>
        </div>
        <div class="dtw"><table class="dt">
          <thead><tr><th style="width:32px"><input type="checkbox" id="ct-chk-all" title="Tout sélectionner" onchange="selectAllCats(this)"></th><th>Catalogue</th><th>Type</th><th>Contenu</th><th>État</th><th>Sync</th><th>Dernière MàJ</th><th>Actions</th></tr></thead>
          <tbody id="ctbody"><tr><td colspan="8"><div class="empty"><div class="ic">⏳</div>Chargement…</div></td></tr></tbody>
        </table></div>
        <div id="bg-bar"><div class="bbt">⟳ Synchronisations en arrière-plan</div><div id="bg-list"></div></div>
      </div>

      <!-- GROUPES -->
      <div id="tab-groups" style="display:none">
        <div class="fbar">
          <input id="gq" placeholder="🔍 Rechercher un groupe…" oninput="filterGroups()">
          <select id="gf-type" onchange="filterGroups()">
            <option value="">Tous types</option>
            <option value="catalogue">🗂️ Catalogues</option>
            <option value="genre">🏷️ Genres</option>
            <option value="permission">🔐 Permissions</option>
          </select>
        </div>
        <div class="htable-wrap"><table class="dt">
          <thead><tr><th>Nom</th><th>Type</th><th>Détails</th><th>Membres</th><th>Permissions</th><th>Actions</th></tr></thead>
          <tbody id="gtbody"><tr><td colspan="6"><div class="empty"><div class="ic">⏳</div>Chargement…</div></td></tr></tbody>
        </table></div>
      </div>

      <!-- RECHERCHE AVANCÉE -->
      <div id="tab-search" style="display:none">
        <div class="search-layout">
          <!-- Panneau filtres -->
          <div class="search-filters">
            <div class="sf-section">
              <label class="sf-label">Titre</label>
              <input id="sf-q" class="fc" placeholder="Naruto, One Piece…" onkeydown="if(event.key==='Enter')runSearch(1)">
            </div>
            <div class="sf-section">
              <label class="sf-label">Type</label>
              <div class="sf-checks">
                <label class="fcheck"><input type="checkbox" class="sf-type" value="Anime"> Anime</label>
                <label class="fcheck"><input type="checkbox" class="sf-type" value="Scans"> Scans</label>
                <label class="fcheck"><input type="checkbox" class="sf-type" value="Film"> Film</label>
                <label class="fcheck"><input type="checkbox" class="sf-type" value="Autres"> Autres</label>
              </div>
            </div>
            <div class="sf-section">
              <label class="sf-label">Langue</label>
              <div class="sf-checks">
                <label class="fcheck"><input type="checkbox" class="sf-langue" value="VOSTFR"> VOSTFR</label>
                <label class="fcheck"><input type="checkbox" class="sf-langue" value="VF"> VF</label>
                <label class="fcheck"><input type="checkbox" class="sf-langue" value="VASTFR"> VASTFR</label>
              </div>
            </div>
            <div class="sf-section">
              <label class="sf-label">Statut</label>
              <div class="sf-checks">
                <label class="fcheck"><input type="checkbox" class="sf-statut" value="En cours"> En cours</label>
                <label class="fcheck"><input type="checkbox" class="sf-statut" value="Terminé"> Terminé</label>
              </div>
            </div>
            <div class="sf-section">
              <label class="sf-label">Année</label>
              <div style="display:flex;gap:.4rem;align-items:center">
                <input id="sf-annee-min" class="fc" type="number" placeholder="1990" min="1960" max="2030" style="flex:1;padding:.3rem .45rem">
                <span style="color:var(--mu);font-size:.8rem">–</span>
                <input id="sf-annee-max" class="fc" type="number" placeholder="2026" min="1960" max="2030" style="flex:1;padding:.3rem .45rem">
              </div>
            </div>
            <div class="sf-section">
              <label class="sf-label">Genres <span id="sf-genre-count" style="color:var(--ac);font-weight:700;font-size:.7rem"></span></label>
              <div class="genre-grid-wrap">
                <div class="genre-grid-filter"><input id="sf-genre-filter" placeholder="Filtrer les genres…" oninput="filterSearchGenres()"></div>
                <div id="sf-genre-grid" class="genre-grid" style="max-height:200px"><span style="color:var(--mu);font-size:.78rem;padding:.4rem">Chargement…</span></div>
              </div>
            </div>
            <div style="display:flex;gap:.45rem;margin-top:.8rem">
              <button class="btn btn-primary" style="flex:1;justify-content:center" onclick="runSearch(1)">🔍 Rechercher</button>
              <button class="btn btn-ghost btn-sm" onclick="clearSearchFilters()" title="Réinitialiser">✕</button>
            </div>
          </div>

          <!-- Zone résultats -->
          <div class="search-results-area">
            <div id="sr-status" style="display:none;padding:.35rem 0;font-size:.82rem;color:var(--mu)"></div>
            <div id="sr-grid" class="search-results-grid"></div>
            <div id="sr-more" style="display:none;text-align:center;margin-top:1.1rem">
              <button class="btn btn-secondary" id="sr-more-btn" onclick="runSearch(_srPage+1)">Charger plus…</button>
            </div>
            <div id="sr-empty" class="empty"><div class="ic">🔍</div>Utilisez les filtres pour rechercher des catalogues sur anime-sama.to</div>
          </div>
        </div>
      </div>

      <!-- APPLICATIONS -->
      <div id="tab-apps" style="display:none">
        <div class="alert a-info" style="margin-bottom:.85rem">
          <strong>Clients API tiers</strong> — Ces applications s'authentifient via <code>POST /auth/client-token</code> avec leur <code>client_id</code> + <code>client_secret</code>.
        </div>
        <div class="fbar">
          <input id="aq" placeholder="🔍 Rechercher par nom…" oninput="filterApps()">
          <select id="af-status" onchange="filterApps()"><option value="">Tous statuts</option><option value="active">Actif</option><option value="inactive">Inactif</option></select>
        </div>
        <div class="dtw"><table class="dt">
          <thead><tr><th>Application</th><th>Client ID</th><th>Statut</th><th>Permissions</th><th>Accès catalogues</th><th>Actions</th></tr></thead>
          <tbody id="atbody"><tr><td colspan="6"><div class="empty"><div class="ic">⏳</div>Chargement…</div></td></tr></tbody>
        </table></div>
      </div>

      <!-- PLANIFICATION -->
      <div id="tab-planning" style="display:none">
        <div class="ptab-nav">
          <div class="ptab active" onclick="showPTab(this,'pt-sorties')">📺 Sorties de la semaine</div>
          <div class="ptab"        onclick="showPTab(this,'pt-prog')">📅 Programmations auto</div>
          <div class="ptab"        onclick="showPTab(this,'pt-history')">🕒 Historique des syncs</div>
        </div>

        <!-- ── Sorties semaine ── -->
        <div id="pt-sorties" class="ptab-content active">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.65rem">
            <div class="planning-legend">
              <span><span style="width:10px;height:10px;border-radius:3px;background:rgba(16,185,129,.2);border:1px solid rgba(16,185,129,.4);display:inline-block"></span> Déjà en base</span>
              <span>🕒 Heure locale · Source : anime-sama.to</span>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="loadPlanning()">↺ Actualiser</button>
          </div>
          <div id="planning-grid" class="week-grid">
            <div style="grid-column:1/-1"><div class="empty"><div class="ic">⏳</div>Chargement du planning…</div></div>
          </div>
          <div id="planning-err" class="alert a-er" style="display:none"></div>
        </div>

        <!-- ── Programmations auto ── -->
        <div id="pt-prog" class="ptab-content">
          <div class="section-hd" style="margin-top:.25rem">
            <h2>📅 Programmations automatiques</h2>
            <button class="btn btn-primary btn-sm" onclick="openCreateSchedule()">+ Nouvelle</button>
          </div>
          <div class="htable-wrap"><table class="dt">
            <thead><tr><th>Catalogue</th><th>Fréquence</th><th>Prochaine exécution</th><th>Dernière exécution</th><th>Statut</th><th>Actions</th></tr></thead>
            <tbody id="stbody"><tr><td colspan="6"><div class="empty"><div class="ic">⏳</div>Chargement…</div></td></tr></tbody>
          </table></div>
        </div>

        <!-- ── Historique syncs ── -->
        <div id="pt-history" class="ptab-content">
          <div class="section-hd" style="margin-top:.25rem">
            <h2>🕒 Historique des synchronisations</h2>
            <button class="btn btn-secondary btn-sm" onclick="loadHistory()">↺ Actualiser</button>
          </div>
          <div class="fbar" style="margin-bottom:.65rem">
            <input id="hq" placeholder="🔍 Filtrer par slug…" oninput="filterHistory()">
            <select id="hf-status" onchange="filterHistory()">
              <option value="">Tous statuts</option><option value="completed">Terminé</option>
              <option value="cancelled">Annulé</option><option value="error">Erreur</option>
            </select>
            <select id="hf-trig" onchange="filterHistory()">
              <option value="">Tous déclencheurs</option>
              <option value="schedule">Planifié</option><option value="manual">Manuel</option>
            </select>
          </div>
          <div class="htable-wrap"><table class="dt">
            <thead><tr><th>Catalogue</th><th>Déclencheur</th><th>Début</th><th>Durée</th><th>Statut</th><th>Éléments</th></tr></thead>
            <tbody id="htbody"><tr><td colspan="6"><div class="empty"><div class="ic">⏳</div>Chargement…</div></td></tr></tbody>
          </table></div>
        </div>
      </div>

    </div><!-- /content -->
  </div>
</div>

<!-- ══ MODALS USERS ══ -->
<div class="mbk" id="m-user" style="display:none" onclick="if(event.target===this)cm('m-user')">
  <div class="mbox md">
    <div class="mhd"><h3 id="mu-title">Utilisateur</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-user')">✕</button></div>
    <div class="mbd">
      <div id="mu-err" class="alert a-er" style="display:none"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.7rem">
        <div class="fg"><label>Nom d'utilisateur *</label><input id="mu-u" class="fc"></div>
        <div class="fg"><label>Email</label><input id="mu-e" class="fc" type="email"></div>
        <div class="fg"><label id="mu-pl">Mot de passe *</label><input id="mu-p" class="fc" type="password"></div>
        <div class="fg"><label>Rôle</label><select id="mu-r" class="fs"><option value="user">Utilisateur</option><option value="admin">Administrateur</option></select></div>
      </div>
      <label class="fcheck" style="margin-bottom:.85rem"><input type="checkbox" id="mu-a" checked> Compte actif</label>
      <div class="div"></div>
      <p style="font-size:.75rem;font-weight:600;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem">Permissions</p>
      <div style="display:flex;gap:1.1rem;flex-wrap:wrap">
        <label class="fcheck"><input type="checkbox" id="mu-sync"> Synchronisation</label>
        <label class="fcheck"><input type="checkbox" id="mu-del"> Suppression</label>
        <label class="fcheck"><input type="checkbox" id="mu-ref"> Rafraîchissement</label>
      </div>
      <div class="div"></div>
      <p style="font-size:.75rem;font-weight:600;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem">Quota de synchronisation</p>
      <label class="fcheck" style="margin-bottom:.55rem"><input type="checkbox" id="mu-q-en" onchange="toggleQuotaUI('mu')"> Activer un quota</label>
      <div id="mu-quota-fields" style="display:none;display:flex;gap:.65rem;flex-wrap:wrap;align-items:flex-end">
        <div class="fg" style="margin-bottom:0;flex:1;min-width:100px"><label>Limite</label><input id="mu-q-max" class="fc" type="number" min="1" placeholder="10"></div>
        <div class="fg" style="margin-bottom:0;flex:1;min-width:100px"><label>Période</label><select id="mu-q-period" class="fs"><option value="day">Par jour</option><option value="month" selected>Par mois</option><option value="year">Par an</option></select></div>
      </div>
    </div>
    <div class="mft"><button class="btn btn-secondary" onclick="cm('m-user')">Annuler</button><button class="btn btn-primary" onclick="saveUser()">Enregistrer</button></div>
  </div>
</div>

<!-- Accès catalogues USERS -->
<div class="mbk" id="m-access" style="display:none" onclick="if(event.target===this)cm('m-access')">
  <div class="mbox lg">
    <div class="mhd"><h3 id="ma-title">Accès aux catalogues</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-access')">✕</button></div>
    <div class="mbd">
      <div id="ma-err" class="alert a-er" style="display:none"></div>
      <label class="fsw" style="margin-bottom:.85rem"><input type="checkbox" id="ma-all" onchange="toggleAllCats()"><span style="font-weight:600">Accès à tous les catalogues</span></label>
      <div id="ma-list"></div>
    </div>
    <div class="mft"><button class="btn btn-secondary" onclick="cm('m-access')">Annuler</button><button class="btn btn-primary" onclick="saveAccess()">Enregistrer</button></div>
  </div>
</div>

<!-- ══ MODALS CATALOGUES ══ -->
<div class="mbk" id="m-add" style="display:none" onclick="if(event.target===this)cm('m-add')">
  <div class="mbox md">
    <div class="mhd"><h3>Ajouter un catalogue</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-add')">✕</button></div>
    <div class="mbd">
      <div id="add-err" class="alert a-er" style="display:none"></div>
      <div id="add-ok"  class="alert a-ok" style="display:none"></div>
      <p style="font-size:.8rem;font-weight:600;color:var(--tx2);margin-bottom:.4rem">🔍 Rechercher un catalogue par titre</p>
      <div style="display:flex;gap:.5rem;margin-bottom:.5rem">
        <input id="sr-q" class="fc" placeholder="Naruto, One Piece…" onkeydown="if(event.key==='Enter')searchCatalogues()">
        <button class="btn btn-secondary" onclick="searchCatalogues()" id="sr-btn">Rechercher</button>
      </div>
      <div id="sr-loading" style="display:none;color:var(--mu);font-size:.82rem;padding:.4rem 0"><span class="spinner"></span> Recherche…</div>
      <div id="sr-results" style="max-height:220px;overflow-y:auto;margin-bottom:.4rem"></div>
      <div class="search-sep">ou entrez directement</div>
      <div class="fg" style="margin-bottom:.35rem">
        <label>Slug ou URL</label>
        <input id="add-slug" class="fc" placeholder="naruto  ou  https://anime-sama.to/catalogue/naruto/">
      </div>
      <div id="add-loading" style="display:none;color:var(--mu);font-size:.82rem;padding:.4rem 0"><span class="spinner"></span> Récupération…</div>
    </div>
    <div class="mft"><button class="btn btn-secondary" onclick="cm('m-add')">Fermer</button><button class="btn btn-primary" id="add-btn" onclick="addCatalogue()">Récupérer</button></div>
  </div>
</div>

<div class="mbk" id="m-detail" style="display:none" onclick="if(event.target===this)cm('m-detail')">
  <div class="mbox lg">
    <div class="mhd"><h3 id="md-title">Catalogue</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-detail')">✕</button></div>
    <div class="mbd">
      <div id="md-err" class="alert a-er" style="display:none"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.7rem">
        <div class="fg"><label>Slug</label><input id="md-slug" class="fc" readonly style="opacity:.55"></div>
        <div class="fg"><label>URL</label><input id="md-url" class="fc" readonly style="opacity:.55"></div>
        <div class="fg"><label>Nom *</label><input id="md-nom" class="fc"></div>
        <div class="fg"><label>Titre alternatif</label><input id="md-alt" class="fc"></div>
      </div>
      <div class="fg"><label>Synopsis</label><textarea id="md-syn" class="fc"></textarea></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.7rem">
        <div class="fg"><label>État</label><select id="md-etat" class="fs"><option value="en_cours">En cours</option><option value="termine">Terminé</option><option value="abandonne">Abandonné</option></select></div>
        <div class="fg"><label>Type</label><select id="md-type" class="fs"><option value="anime">Anime</option><option value="scan">Scan</option><option value="film">Film</option><option value="autre">Autre</option></select></div>
        <div class="fg"><label>Genres</label><div class="tag-box" id="md-genres-box" onclick="document.getElementById('md-gi').focus()"><input id="md-gi" class="tag-input" placeholder="Action… + Entrée" onkeydown="addTag('genres',event)"></div></div>
        <div class="fg"><label>Langues</label><div class="tag-box" id="md-langues-box" onclick="document.getElementById('md-li').focus()"><input id="md-li" class="tag-input" placeholder="vf, vostfr… + Entrée" onkeydown="addTag('langues',event)"></div></div>
      </div>
      <div class="div"></div>
      <p style="font-size:.75rem;color:var(--mu)">Créé : <span id="md-created"></span> · MàJ : <span id="md-updated"></span></p>
    </div>
    <div class="mft"><button class="btn btn-secondary" onclick="cm('m-detail')">Annuler</button><button class="btn btn-primary" onclick="saveDetail()">Enregistrer</button></div>
  </div>
</div>

<!-- Viewer contenu catalogue -->
<div class="mbk" id="m-content" style="display:none" onclick="if(event.target===this)cm('m-content')">
  <div class="mbox xl">
    <div class="mhd"><h3 id="mc-title">Contenu</h3><span id="mc-sync-badge" class="badge"></span><button class="btn btn-ghost btn-icon" onclick="cm('m-content')">✕</button></div>
    <div class="mbd" id="mc-body"><div class="empty"><div class="ic">⏳</div>Chargement…</div></div>
    <div class="mft"><button class="btn btn-secondary" onclick="cm('m-content')">Fermer</button></div>
  </div>
</div>

<!-- Modal confirmation suppression catalogue(s) -->
<div class="mbk" id="m-del-cat" style="display:none" onclick="if(event.target===this)cm('m-del-cat')">
  <div class="mbox sm">
    <div class="mhd"><h3>Supprimer</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-del-cat')">✕</button></div>
    <div class="mbd">
      <p id="md-text" style="color:var(--tx);line-height:1.6;margin-bottom:.6rem"></p>
      <div class="alert a-er">⚠ Cette action est irréversible. Toutes les données (épisodes, films, scans) associées seront supprimées.</div>
    </div>
    <div class="mft">
      <button class="btn btn-secondary" onclick="cm('m-del-cat')">Annuler</button>
      <button class="btn btn-danger" onclick="confirmDeleteCats()">Supprimer</button>
    </div>
  </div>
</div>

<!-- Modal lecteur vidéo -->
<div class="mbk" id="m-player" style="display:none" onclick="if(event.target===this)closePlayer()">
  <div class="mbox" style="max-width:960px;height:85vh;display:flex;flex-direction:column">
    <div class="mhd">
      <h3 id="mp-title">Lecteur</h3>
      <button class="btn btn-ghost btn-icon" onclick="closePlayer()">✕</button>
    </div>
    <div id="mp-lects"><span class="lbl">Lecteurs :</span></div>
    <div id="mp-frame-wrap"><iframe id="mp-iframe" src="" allowfullscreen referrerpolicy="no-referrer"></iframe></div>
  </div>
</div>

<!-- Modal sync -->
<div class="mbk" id="m-sync" style="display:none">
  <div class="mbox md">
    <div class="mhd"><h3 id="ms-title">Synchronisation</h3><span id="ms-state-badge" class="badge b-info" style="font-size:.68rem">Démarrage</span></div>
    <div class="mbd">
      <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:.2rem">
        <span id="ms-label" style="font-size:.82rem;font-weight:600;color:var(--mu)">Initialisation…</span>
        <span id="ms-pct" style="font-size:.82rem;font-weight:700;color:var(--ac)">0%</span>
      </div>
      <div class="prog-wrap"><div id="ms-bar" class="prog-fill"></div></div>
      <p id="ms-current" style="font-size:.77rem;color:var(--mu);margin:.2rem 0 .5rem;min-height:1.1rem"></p>
      <div class="sync-ctrl">
        <button class="btn btn-warn btn-sm"      id="ms-btn-pause"  onclick="syncPause()">⏸ Pause</button>
        <button class="btn btn-ok btn-sm"        id="ms-btn-resume" onclick="syncResume()" style="display:none">▶ Reprendre</button>
        <button class="btn btn-danger btn-sm"    id="ms-btn-cancel" onclick="syncCancel()">✕ Annuler</button>
        <button class="btn btn-info btn-sm"      id="ms-btn-fond"   onclick="syncFond()">↗ Fond</button>
        <button class="btn btn-secondary btn-sm" id="ms-btn-close"  onclick="cm('m-sync')" style="display:none">Fermer</button>
      </div>
      <div style="font-size:.73rem;font-weight:600;color:var(--mu);text-transform:uppercase;letter-spacing:.04em;margin:.4rem 0 .25rem">Journal</div>
      <div class="sync-log" id="ms-log"></div>
    </div>
  </div>
</div>

<!-- Modal visibilité -->
<div class="mbk" id="m-vis" style="display:none" onclick="if(event.target===this)cm('m-vis')">
  <div class="mbox md">
    <div class="mhd"><h3 id="mv-title">Visibilité</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-vis')">✕</button></div>
    <div class="mbd" id="mv-body"></div>
    <div class="mft"><button class="btn btn-secondary" onclick="cm('m-vis')">Annuler</button><button class="btn btn-primary" onclick="saveVisibility()">Enregistrer</button></div>
  </div>
</div>

<!-- ══ MODALS APPLICATIONS ══ -->

<!-- Créer / Modifier client -->
<div class="mbk" id="m-client" style="display:none" onclick="if(event.target===this)cm('m-client')">
  <div class="mbox md">
    <div class="mhd"><h3 id="mc2-title">Nouvelle application</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-client')">✕</button></div>
    <div class="mbd">
      <div id="mc2-err" class="alert a-er" style="display:none"></div>
      <div class="fg"><label>Nom de l'application *</label><input id="mc2-name" class="fc" placeholder="Mon Application"></div>
      <div class="fg"><label>Description</label><textarea id="mc2-desc" class="fc" placeholder="Optionnel — usage de l'application"></textarea></div>
      <label class="fcheck" style="margin-bottom:.85rem"><input type="checkbox" id="mc2-active" checked> Application active</label>
      <div class="div"></div>
      <p style="font-size:.75rem;font-weight:600;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem">Permissions</p>
      <div style="display:flex;gap:1.1rem;flex-wrap:wrap">
        <label class="fcheck"><input type="checkbox" id="mc2-sync"> Synchronisation</label>
        <label class="fcheck"><input type="checkbox" id="mc2-del"> Suppression</label>
        <label class="fcheck"><input type="checkbox" id="mc2-ref"> Rafraîchissement</label>
      </div>
      <div class="div"></div>
      <p style="font-size:.75rem;font-weight:600;color:var(--mu);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem">Quota de synchronisation</p>
      <label class="fcheck" style="margin-bottom:.55rem"><input type="checkbox" id="mc2-q-en" onchange="toggleQuotaUI('mc2')"> Activer un quota</label>
      <div id="mc2-quota-fields" style="display:none;display:flex;gap:.65rem;flex-wrap:wrap;align-items:flex-end">
        <div class="fg" style="margin-bottom:0;flex:1;min-width:100px"><label>Limite</label><input id="mc2-q-max" class="fc" type="number" min="1" placeholder="10"></div>
        <div class="fg" style="margin-bottom:0;flex:1;min-width:100px"><label>Période</label><select id="mc2-q-period" class="fs"><option value="day">Par jour</option><option value="month" selected>Par mois</option><option value="year">Par an</option></select></div>
      </div>
    </div>
    <div class="mft"><button class="btn btn-secondary" onclick="cm('m-client')">Annuler</button><button class="btn btn-primary" onclick="saveClient()">Enregistrer</button></div>
  </div>
</div>

<!-- Afficher le secret (une seule fois) -->
<div class="mbk" id="m-secret" style="display:none">
  <div class="mbox sm">
    <div class="mhd"><h3 id="ms2-title">Secret généré</h3></div>
    <div class="mbd">
      <div class="alert a-wa" style="margin-bottom:.85rem">⚠ <strong>Copiez ce secret maintenant</strong> — il ne sera plus affiché une fois cette fenêtre fermée.</div>
      <div class="secret-box" style="margin-bottom:.75rem">
        <div class="s-label">Client ID</div>
        <span class="secret-val" id="ms2-cid"></span>
      </div>
      <div class="secret-box">
        <div class="s-label">Client Secret</div>
        <span class="secret-val" id="ms2-secret"></span>
      </div>
      <div style="display:flex;gap:.5rem;margin-top:.75rem">
        <button class="btn btn-secondary btn-sm" onclick="copyText(document.getElementById('ms2-cid').textContent,'Client ID copié')">📋 Copier ID</button>
        <button class="btn btn-primary btn-sm"   onclick="copyText(document.getElementById('ms2-secret').textContent,'Secret copié !')">📋 Copier secret</button>
      </div>
      <p style="font-size:.76rem;color:var(--mu);margin:.65rem 0 0">Utilisez <span class="mono">POST /auth/client-token</span> avec ces identifiants pour obtenir un Bearer token.</p>
    </div>
    <div class="mft"><button class="btn btn-primary" onclick="cm('m-secret');loadApps()">Fermer</button></div>
  </div>
</div>

<!-- Accès catalogues CLIENTS -->
<div class="mbk" id="m-clt-access" style="display:none" onclick="if(event.target===this)cm('m-clt-access')">
  <div class="mbox lg">
    <div class="mhd"><h3 id="mca-title">Accès aux catalogues</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-clt-access')">✕</button></div>
    <div class="mbd">
      <div id="mca-err" class="alert a-er" style="display:none"></div>
      <label class="fsw" style="margin-bottom:.85rem"><input type="checkbox" id="mca-all" onchange="toggleAllCatsClt()"><span style="font-weight:600">Accès à tous les catalogues</span></label>
      <div id="mca-list"></div>
    </div>
    <div class="mft"><button class="btn btn-secondary" onclick="cm('m-clt-access')">Annuler</button><button class="btn btn-primary" onclick="saveClientAccess()">Enregistrer</button></div>
  </div>
</div>

<!-- ══ MODAL PROGRAMMATION ══ -->
<div class="mbk" id="m-schedule" style="display:none" onclick="if(event.target===this)cm('m-schedule')">
  <div class="mbox md">
    <div class="mhd"><h3 id="ms3-title">Nouvelle programmation</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-schedule')">✕</button></div>
    <div class="mbd">
      <div id="ms3-err" class="alert a-er" style="display:none"></div>
      <div class="fg">
        <label>Catalogue (slug) *</label>
        <div style="display:flex;gap:.5rem">
          <input id="ms3-slug" class="fc" placeholder="naruto" list="ms3-cat-list">
          <datalist id="ms3-cat-list"></datalist>
        </div>
      </div>
      <div class="fg">
        <label>Description</label>
        <input id="ms3-desc" class="fc" placeholder="Optionnel">
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.7rem">
        <div class="fg"><label>Fréquence *</label>
          <select id="ms3-freq" class="fs" onchange="onFreqChange()">
            <option value="daily">Quotidien</option>
            <option value="weekly">Hebdomadaire</option>
            <option value="biweekly">Bi-hebdomadaire (2 sem.)</option>
            <option value="monthly">Mensuel</option>
            <option value="custom">Personnalisé (N jours)</option>
          </select>
        </div>
        <div class="fg"><label>Heure (UTC) *</label>
          <div style="display:flex;gap:.35rem">
            <input id="ms3-hour" class="fc" type="number" min="0" max="23" value="2" style="width:60px">
            <span style="line-height:2.2;color:var(--mu)">h</span>
            <input id="ms3-min" class="fc" type="number" min="0" max="59" value="0" style="width:60px">
          </div>
        </div>
      </div>
      <div id="ms3-dow-field" class="fg" style="display:none"><label>Jour de la semaine</label>
        <select id="ms3-dow" class="fs">
          <option value="0">Lundi</option><option value="1">Mardi</option><option value="2">Mercredi</option>
          <option value="3">Jeudi</option><option value="4">Vendredi</option><option value="5">Samedi</option><option value="6">Dimanche</option>
        </select>
      </div>
      <div id="ms3-dom-field" class="fg" style="display:none"><label>Jour du mois (1–28)</label>
        <input id="ms3-dom" class="fc" type="number" min="1" max="28" value="1">
      </div>
      <div id="ms3-interval-field" class="fg" style="display:none"><label>Tous les N jours</label>
        <input id="ms3-interval" class="fc" type="number" min="1" value="7">
      </div>
      <label class="fcheck"><input type="checkbox" id="ms3-active" checked> Programmation active</label>
    </div>
    <div class="mft"><button class="btn btn-secondary" onclick="cm('m-schedule')">Annuler</button><button class="btn btn-primary" onclick="saveSchedule()">Enregistrer</button></div>
  </div>
</div>

<!-- ══ MODAL GROUPE ══ -->
<div class="mbk" id="m-group" style="display:none" onclick="if(event.target===this)cm('m-group')">
  <div class="mbox" style="max-width:600px">
    <div class="mhd"><h3 id="mg-title">Nouveau groupe</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-group')">✕</button></div>
    <div class="mbd">
      <div id="mg-err" class="alert a-er" style="display:none"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.65rem">
        <div class="fg"><label>Nom du groupe *</label><input id="mg-name" class="fc" placeholder="Ex : Abonnés Premium"></div>
        <div class="fg"><label>Type *</label>
          <select id="mg-type" class="fc" onchange="onGroupTypeChange()">
            <option value="catalogue">🗂️ Catalogues spécifiques</option>
            <option value="genre">🏷️ Genres de catalogues</option>
            <option value="permission">🔐 Permissions seules</option>
          </select>
        </div>
      </div>
      <div class="fg"><label>Description</label><input id="mg-desc" class="fc" placeholder="Optionnel"></div>

      <!-- Section Catalogues -->
      <div id="mg-sect-catalogue">
        <div class="fg">
          <label style="font-size:.78rem;color:var(--ac)">🗂️ Catalogues accessibles aux membres</label>
          <div id="mg-cat-chips" class="genre-chips" style="min-height:28px;background:var(--sur2);border:1px solid var(--bdr);border-radius:7px;padding:.4rem;margin-bottom:.35rem"></div>
          <div class="mg-cat-search-wrap">
            <input id="mg-cat-search" class="fc" placeholder="Rechercher par titre…" oninput="mgSearchCats()" autocomplete="off">
            <div id="mg-cat-drop" class="search-drop" style="display:none"></div>
          </div>
        </div>
      </div>

      <!-- Section Genres -->
      <div id="mg-sect-genre" style="display:none">
        <div class="fg">
          <label style="font-size:.78rem;color:var(--info)">🏷️ Genres — accès à tous les catalogues de ces genres</label>
          <div class="genre-grid-wrap">
            <div class="genre-grid-filter"><input id="mg-genre-filter" placeholder="Filtrer les genres…" oninput="filterGenreGrid()"></div>
            <div id="mg-genre-grid" class="genre-grid"><span style="color:var(--mu);font-size:.78rem;padding:.4rem">Chargement des genres…</span></div>
            <div class="genre-grid-sync">
              <span id="mg-genre-sync-lbl"></span>
              <button class="btn btn-secondary btn-sm" onclick="syncGenres()" id="mg-genre-sync-btn">↺ Sync genres</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Permissions (tous types) -->
      <div style="border-top:1px solid var(--bdr);padding-top:.7rem;margin-top:.4rem">
        <div class="fg-label" style="font-size:.76rem;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:.04em;margin-bottom:.45rem">🔐 Permissions accordées aux membres</div>
        <div style="display:flex;gap:1.2rem;flex-wrap:wrap">
          <label class="chk-label"><input type="checkbox" id="mg-sync"> Synchroniser</label>
          <label class="chk-label"><input type="checkbox" id="mg-del"> Supprimer</label>
          <label class="chk-label"><input type="checkbox" id="mg-ref"> Rafraîchir</label>
        </div>
        <div class="fg" style="margin-top:.55rem">
          <label class="chk-label"><input type="checkbox" id="mg-q-en" onchange="toggleQuotaUI('mg')"> Quota de synchronisation</label>
          <div id="mg-quota-fields" class="quota-row" style="display:none">
            <input id="mg-q-max" type="number" min="1" value="10" style="width:80px">
            <span>syncs par</span>
            <select id="mg-q-period"><option value="day">jour</option><option value="month" selected>mois</option><option value="year">an</option></select>
          </div>
        </div>
      </div>
      <div class="mftr">
        <button class="btn btn-ghost" onclick="cm('m-group')">Annuler</button>
        <button class="btn btn-primary" onclick="saveGroup()">Enregistrer</button>
      </div>
    </div>
  </div>
</div>

<!-- ══ MODAL MEMBRES ══ -->
<div class="mbk" id="m-members" style="display:none" onclick="if(event.target===this)cm('m-members')">
  <div class="mbox" style="max-width:520px">
    <div class="mhd"><h3 id="mm-title">Membres</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-members')">✕</button></div>
    <div class="mbd">
      <div style="display:flex;gap:.4rem;margin-bottom:.75rem">
        <input id="mm-add-u" class="fc" list="mm-users-dl" placeholder="Nom d'utilisateur à ajouter…" style="flex:1">
        <datalist id="mm-users-dl"></datalist>
        <button class="btn btn-primary btn-sm" onclick="addGroupMember()">+ Ajouter</button>
      </div>
      <div id="mm-body"></div>
      <div class="mftr"><button class="btn btn-ghost" onclick="cm('m-members')">Fermer</button></div>
    </div>
  </div>
</div>

<!-- ══ MODAL BLOCAGE ══ -->
<div class="mbk" id="m-block" style="display:none" onclick="if(event.target===this)cm('m-block')">
  <div class="mbox sm">
    <div class="mhd"><h3 id="mb-title">Bloquer le compte</h3><button class="btn btn-ghost btn-icon" onclick="cm('m-block')">✕</button></div>
    <div class="mbd">
      <div id="mb-err" class="alert a-er" style="display:none"></div>
      <div class="alert a-wa" style="margin-bottom:.75rem">⚠ L'utilisateur recevra une erreur 403 à chaque requête tant qu'il est bloqué.</div>
      <div class="fg"><label>Raison (optionnel)</label><input id="mb-reason" class="fc" placeholder="Violation des CGU, abus…"></div>
      <div class="fg"><label>Bloquer jusqu'au (optionnel — vide = permanent)</label><input id="mb-until" class="fc" type="datetime-local"></div>
    </div>
    <div class="mft"><button class="btn btn-secondary" onclick="cm('m-block')">Annuler</button><button class="btn btn-danger" onclick="saveBlock()">Confirmer le blocage</button></div>
  </div>
</div>

<div id="toasts"></div>

<script>
// ─── Config ────────────────────────────────────────────────────────────────
const API    = '__API_BASE__';
const WS_API = API.replace(/^http/, 'ws');

// ─── État global ───────────────────────────────────────────────────────────
let token = localStorage.getItem('as_token') || '';
let allUsers = [], allCats = [], allClients = [], allGroups = [];
let editUsername = null, accessUsername = null;
let visSlug = null, detailSlug = null;
let detailTags = { genres: [], langues: [] };
let activeSyncSlug = null;
let editClientId = null, cltAccessClientId = null;
const bgSyncs = new Map();
let _delCatSlugs = [];
let _playerVideos = [];
let _contentData  = null;

// ─── Thème ─────────────────────────────────────────────────────────────────
const H = document.documentElement;
H.setAttribute('data-theme', localStorage.getItem('as_theme') || 'dark');
function updateThemeBtn(){document.getElementById('tbtn').textContent=H.getAttribute('data-theme')==='dark'?'☀️ Thème clair':'🌙 Thème sombre';}
function toggleTheme(){const n=H.getAttribute('data-theme')==='dark'?'light':'dark';H.setAttribute('data-theme',n);localStorage.setItem('as_theme',n);updateThemeBtn();}
updateThemeBtn();

// ─── API / Utils ───────────────────────────────────────────────────────────
async function api(method,path,body){
  const opts={method,headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`}};
  if(body!==undefined) opts.body=JSON.stringify(body);
  const r=await fetch(API+path,opts);
  if(r.status===204) return null;
  const d=await r.json().catch(()=>({}));
  if(!r.ok) throw d.detail||JSON.stringify(d);
  return d;
}
function toast(msg,type='info'){
  const e=document.createElement('div');
  e.className=`toast t-${type==='ok'?'ok':type==='er'?'er':type==='wa'?'wa':'info'}`;
  e.innerHTML=`<span>${type==='ok'?'✓':type==='er'?'✕':type==='wa'?'⚠':'ℹ'}</span>${msg}`;
  document.getElementById('toasts').appendChild(e);setTimeout(()=>e.remove(),3800);
}
function copyText(txt,msg){navigator.clipboard.writeText(txt).then(()=>toast(msg,'ok')).catch(()=>toast('Copie échouée','er'));}
function om(id){document.getElementById(id).style.display='flex';}
function cm(id){document.getElementById(id).style.display='none';}
function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
document.addEventListener('keydown',e=>{if(e.key==='Escape'){if(document.getElementById('m-player').style.display!=='none'){closePlayer();return;}['m-user','m-access','m-add','m-detail','m-content','m-vis','m-client','m-clt-access','m-schedule','m-block','m-del-cat'].forEach(cm);}});

// ─── Auth ──────────────────────────────────────────────────────────────────
document.getElementById('lp').onkeydown=e=>{if(e.key==='Enter')doLogin();};
async function doLogin(){
  const err=document.getElementById('lerr');err.style.display='none';
  try{
    const r=await fetch(API+'/auth/login',{method:'POST',body:new URLSearchParams({username:document.getElementById('lu').value.trim(),password:document.getElementById('lp').value})});
    const d=await r.json();if(!r.ok) throw d.detail||'Identifiants incorrects';
    token=d.access_token;localStorage.setItem('as_token',token);await initApp();
  }catch(e){err.textContent=typeof e==='string'?e:'Identifiants incorrects';err.style.display='block';}
}
function logout(){localStorage.removeItem('as_token');token='';document.getElementById('login-page').style.display='flex';document.getElementById('shell').style.display='none';}

async function initApp(){
  try{
    const me=await api('GET','/auth/me');
    if(me.role!=='admin'){toast('Réservé aux administrateurs','er');logout();return;}
    document.getElementById('me-lbl').textContent=`@ ${me.username}`;
    document.getElementById('login-page').style.display='none';
    document.getElementById('shell').style.display='flex';
    await Promise.all([loadUsers(),loadCats(),loadApps(),loadGroups()]);
  }catch{logout();}
}

// ── OIDC: hash handling ────────────────────────────────────────────────────
(function(){
  const hash=window.location.hash;
  if(hash.startsWith('#token=')){
    token=hash.slice(7);localStorage.setItem('as_token',token);
    history.replaceState(null,'',location.pathname);initApp();return;
  }
  if(hash.startsWith('#oidc_error=')){
    const err=decodeURIComponent(hash.slice(12));
    const el=document.getElementById('lerr-oidc');
    if(el){el.textContent='Erreur OIDC : '+err;el.style.display='block';}
    history.replaceState(null,'',location.pathname);
  }
  if(token) initApp();
})();

// ── OIDC: charger les fournisseurs ────────────────────────────────────────
(async function(){
  try{
    const providers=await fetch(API+'/auth/oidc/providers').then(r=>r.json());
    if(!providers||!providers.length)return;
    const ICONS={google:'https://www.google.com/favicon.ico',github:'https://github.com/favicon.ico'};
    const html=providers.map(p=>`<button class="btn-oidc" onclick="oidcLogin('${esc(p.id)}')">
      <img class="oidc-icon" src="${ICONS[p.id]||''}" onerror="this.style.display='none'">
      Continuer avec ${esc(p.name)}
    </button>`).join('');
    const c=document.getElementById('oidc-providers-list');if(c)c.innerHTML=html;
    const bx=document.getElementById('oidc-btns');if(bx)bx.style.display='';
  }catch{}
})();

async function oidcLogin(providerId){
  try{
    const r=await api('GET','/auth/oidc/authorize?provider='+encodeURIComponent(providerId));
    if(r.url) window.location.href=r.url;
  }catch(e){toast(String(e),'er');}
}

// ─── Tabs ──────────────────────────────────────────────────────────────────
function goToCatalogues(){document.querySelector('.ni[data-tab="catalogues"]').click();}
function switchTab(el){
  const tab=el.dataset.tab;
  document.querySelectorAll('.ni').forEach(n=>n.classList.remove('active'));el.classList.add('active');
  ['users','catalogues','groups','search','apps','planning'].forEach(t=>document.getElementById('tab-'+t).style.display=t===tab?'':'none');
  const titles={users:'Utilisateurs',catalogues:'Catalogues',groups:'Groupes',search:'Recherche avancée',apps:'Applications',planning:'Planification'};
  const actions={
    users:`<button class="btn btn-primary btn-sm" onclick="openCreateUser()">+ Ajouter</button>`,
    catalogues:`<button class="btn btn-primary btn-sm" onclick="openAddCat()">+ Ajouter un catalogue</button>`,
    groups:`<button class="btn btn-primary btn-sm" onclick="openCreateGroup()">+ Nouveau groupe</button>`,
    apps:`<button class="btn btn-primary btn-sm" onclick="openCreateClient()">+ Créer une application</button>`,
    search:'',planning:'',
  };
  document.getElementById('tb-title').textContent=titles[tab]||tab;
  document.getElementById('tb-actions').innerHTML=actions[tab]||'';
  if(tab==='planning'){loadPlanning();loadSchedules();loadHistory();}
  if(tab==='groups'){loadGroups();}
  if(tab==='search'){initSearch();}
}

function showPTab(el,target){
  document.querySelectorAll('.ptab').forEach(t=>t.classList.remove('active'));el.classList.add('active');
  document.querySelectorAll('.ptab-content').forEach(c=>c.classList.remove('active'));
  document.getElementById(target).classList.add('active');
}
document.getElementById('tb-actions').innerHTML=`<button class="btn btn-primary btn-sm" onclick="openCreateUser()">+ Ajouter</button>`;

// ═══════════════════════════════ USERS ════════════════════════════════════
async function loadUsers(){allUsers=await api('GET','/auth/users');renderUsers(allUsers);}
function filterUsers(){
  const q=document.getElementById('uq').value.toLowerCase(),r=document.getElementById('uf-role').value;
  renderUsers(allUsers.filter(u=>(!q||(u.username+' '+(u.email||'')).toLowerCase().includes(q))&&(!r||u.role===r)));
}
function renderUsers(list){
  const b=document.getElementById('utbody');
  if(!list.length){b.innerHTML=`<tr><td colspan="6"><div class="empty"><div class="ic">👤</div>Aucun résultat</div></td></tr>`;return;}
  b.innerHTML=list.map(u=>{
    const p=u.permissions||{},cats=p.allowed_catalogues||[],blk=u.is_blocked,q=p.quota||{};
    const quotaInfo=q.enabled?`<span class="quota-used ${q.max_syncs>0?'':''}">Quota: ${q.max_syncs}/${q.period==='day'?'j':q.period==='year'?'an':'mois'}</span>`:'';
    return `<tr>
      <td><div style="display:flex;align-items:center;gap:.55rem">
        <div class="av">${esc(u.username).slice(0,2).toUpperCase()}</div>
        <div><div style="font-weight:600">${esc(u.username)}</div>${u.email?`<div style="font-size:.72rem;color:var(--mu)">${esc(u.email)}</div>`:''}</div>
      </div></td>
      <td><span class="badge ${u.role==='admin'?'b-ac':'b-mu'}">${u.role}</span></td>
      <td>
        <span class="badge ${u.is_active?'b-ok':'b-er'}">${u.is_active?'Actif':'Inactif'}</span>
        ${blk?'<span class="badge b-block" style="margin-left:3px">🚫 Bloqué</span>':''}
      </td>
      <td><div style="display:flex;gap:.2rem;flex-wrap:wrap"><span class="pc ${p.can_sync?'on':''}">⟳ Sync</span><span class="pc ${p.can_delete?'on':''}">🗑 Suppr</span><span class="pc ${p.can_refresh?'on':''}">↺ Refresh</span>${quotaInfo}</div></td>
      <td>${cats.length===0?'<span class="badge b-info">Tous</span>':cats.slice(0,3).map(c=>`<span class="tag">${esc(c)}</span>`).join('')+(cats.length>3?`<span class="tag">+${cats.length-3}</span>`:'')}</td>
      <td><div class="actions">
        <button class="btn btn-secondary btn-icon btn-sm" onclick="openEditUser('${esc(u.username)}')">✏️</button>
        <button class="btn btn-secondary btn-icon btn-sm" onclick="openAccess('${esc(u.username)}')">🔑</button>
        <button class="btn ${blk?'btn-ok':'btn-danger'} btn-icon btn-sm" title="${blk?'Débloquer':'Bloquer'}" onclick="${blk?`unblock('user','${esc(u.username)}')`:`openBlock('user','${esc(u.username)}')`}">${blk?'✓':'🚫'}</button>
        <button class="btn btn-danger btn-icon btn-sm"   onclick="deleteUser('${esc(u.username)}')">🗑</button>
      </div></td></tr>`;
  }).join('');
}
function openCreateUser(){
  editUsername=null;document.getElementById('mu-title').textContent='Nouvel utilisateur';document.getElementById('mu-pl').textContent='Mot de passe *';
  ['mu-u','mu-e','mu-p'].forEach(i=>document.getElementById(i).value='');document.getElementById('mu-u').disabled=false;
  document.getElementById('mu-r').value='user';document.getElementById('mu-a').checked=true;
  ['mu-sync','mu-del','mu-ref'].forEach(i=>document.getElementById(i).checked=false);
  document.getElementById('mu-err').style.display='none';om('m-user');
}
function openEditUser(username){
  editUsername=username;const u=allUsers.find(x=>x.username===username);
  document.getElementById('mu-title').textContent=`Modifier — ${username}`;document.getElementById('mu-pl').textContent='Mot de passe (vide = inchangé)';
  document.getElementById('mu-u').value=u.username;document.getElementById('mu-u').disabled=true;
  document.getElementById('mu-e').value=u.email||'';document.getElementById('mu-p').value='';
  document.getElementById('mu-r').value=u.role;document.getElementById('mu-a').checked=u.is_active;
  const p=u.permissions||{};document.getElementById('mu-sync').checked=!!p.can_sync;document.getElementById('mu-del').checked=!!p.can_delete;document.getElementById('mu-ref').checked=!!p.can_refresh;
  // Quota
  const q=p.quota||{};const qen=document.getElementById('mu-q-en');qen.checked=!!q.enabled;
  document.getElementById('mu-q-max').value=q.max_syncs||10;document.getElementById('mu-q-period').value=q.period||'month';
  document.getElementById('mu-quota-fields').style.display=q.enabled?'flex':'none';
  // Blocage
  if(u.is_blocked){const bb=document.createElement('div');bb.id='mu-blocked-banner';bb.className='blocked-banner';bb.innerHTML=`🚫 Ce compte est actuellement bloqué${u.blocked_reason?' ('+esc(u.blocked_reason)+')':''}${u.blocked_until?' jusqu\'au '+new Date(u.blocked_until).toLocaleString('fr'):''}`;const bd=document.getElementById('m-user').querySelector('.mbd');const ex=document.getElementById('mu-blocked-banner');if(ex)ex.remove();bd.insertBefore(bb,bd.firstChild);}else{const ex=document.getElementById('mu-blocked-banner');if(ex)ex.remove();}
  document.getElementById('mu-err').style.display='none';om('m-user');
}
async function saveUser(){
  const errEl=document.getElementById('mu-err');errEl.style.display='none';
  try{
    const qen=document.getElementById('mu-q-en').checked;
    const quota={enabled:qen,period:document.getElementById('mu-q-period').value,max_syncs:parseInt(document.getElementById('mu-q-max').value)||10};
    const perms={can_sync:document.getElementById('mu-sync').checked,can_delete:document.getElementById('mu-del').checked,can_refresh:document.getElementById('mu-ref').checked,quota};
    if(editUsername){
      const ex=allUsers.find(u=>u.username===editUsername)?.permissions||{};
      perms.allowed_catalogues=ex.allowed_catalogues||[];perms.catalogue_content=ex.catalogue_content||{};
      const body={is_active:document.getElementById('mu-a').checked,role:document.getElementById('mu-r').value,permissions:perms};
      const email=document.getElementById('mu-e').value;if(email) body.email=email;
      const pass=document.getElementById('mu-p').value;if(pass) body.password=pass;
      await api('PUT',`/auth/users/${editUsername}`,body);toast('Utilisateur mis à jour','ok');
    }else{
      const pass=document.getElementById('mu-p').value;if(!pass) throw 'Le mot de passe est requis';
      perms.allowed_catalogues=[];perms.catalogue_content={};
      await api('POST','/auth/register',{username:document.getElementById('mu-u').value.trim(),password:pass,email:document.getElementById('mu-e').value||null,role:document.getElementById('mu-r').value,permissions:perms});
      toast('Utilisateur créé','ok');
    }
    cm('m-user');await loadUsers();
  }catch(e){errEl.textContent=typeof e==='string'?e:JSON.stringify(e);errEl.style.display='block';}
}
async function deleteUser(username){
  if(!confirm(`Supprimer « ${username} » ?`))return;
  try{await api('DELETE',`/auth/users/${username}`);toast(`${username} supprimé`,'ok');await loadUsers();}
  catch(e){toast(String(e),'er');}
}

// ─── Accès catalogues Users ────────────────────────────────────────────────
function openAccess(username){
  accessUsername=username;const u=allUsers.find(x=>x.username===username);
  document.getElementById('ma-title').textContent=`Accès — ${username}`;document.getElementById('ma-err').style.display='none';
  const p=u?.permissions||{},allowed=p.allowed_catalogues||[];
  document.getElementById('ma-all').checked=allowed.length===0;renderAccessList('ma-list','ma-all',allowed,p.catalogue_content||{});om('m-access');
}
function toggleAllCats(){document.getElementById('ma-list').style.display=document.getElementById('ma-all').checked?'none':'';}
function renderAccessList(listId,allId,allowed,content){
  const list=document.getElementById(listId);list.style.display=document.getElementById(allId).checked?'none':'';
  list.innerHTML=allCats.map(cat=>{
    const on=allowed.includes(cat.slug),ca=content[cat.slug]||{};
    return `<div class="car">
      <div class="cah" onclick="toggleCab('${cat.slug}-${listId}')">
        <label class="fsw" onclick="event.stopPropagation()"><input type="checkbox" id="ca-${listId}-${cat.slug}" ${on?'checked':''} onchange="onCatToggle('${cat.slug}','${listId}')"></label>
        <span style="font-weight:600;font-size:.84rem">${esc(cat.nom)}</span>
        <span class="badge b-mu" style="margin-left:auto">${esc(cat.slug)}</span><span style="color:var(--mu)">▾</span>
      </div>
      <div class="cab ${on?'open':''}" id="cab-${cat.slug}-${listId}">${renderCR(cat,ca,listId)}</div>
    </div>`;
  }).join('');
}
function onCatToggle(slug,listId){document.getElementById(`cab-${slug}-${listId}`).classList.toggle('open',document.getElementById(`ca-${listId}-${slug}`).checked);}
function toggleCab(id){document.getElementById('cab-'+id).classList.toggle('open');}
function renderCR(cat,access,pfx){
  const secs=[{key:'saisons',label:'🎬 Saisons',items:cat.saisons},{key:'films',label:'🎞 Films',items:cat.films},{key:'scans',label:'📖 Scans',items:cat.scans}].filter(s=>s.items?.length);
  if(!secs.length) return '<p style="color:var(--mu);font-size:.8rem;margin:0">Aucun contenu.</p>';
  return secs.map(s=>{
    const al=access[s.key]||[],ia=al.length===0;
    return `<div class="cs" style="margin-bottom:.6rem"><label>${s.label}</label><div class="pills">
      <label class="pill"><input type="checkbox" class="cr-all-${pfx}" data-cat="${cat.slug}" data-type="${s.key}" ${ia?'checked':''} onchange="onAllPill(this,'${pfx}')">✓ Tous</label>
      ${s.items.map(i=>`<label class="pill"><input type="checkbox" class="cr-item-${pfx}" data-cat="${cat.slug}" data-type="${s.key}" value="${esc(i.slug)}" ${(ia||al.includes(i.slug))?'checked':''}>${esc(i.nom||i.slug)}${i.lang?` <span style="opacity:.55;font-size:.68rem">(${i.lang})</span>`:''}</label>`).join('')}
    </div></div>`;
  }).join('');
}
function onAllPill(cb,pfx){document.querySelectorAll(`.cr-item-${pfx}[data-cat="${cb.dataset.cat}"][data-type="${cb.dataset.type}"]`).forEach(i=>i.checked=cb.checked);}

function _gatherAccess(pfx){
  let allowed=[],content={};
  allCats.forEach(cat=>{
    if(!document.getElementById(`ca-${pfx}-${cat.slug}`)?.checked) return;
    allowed.push(cat.slug);content[cat.slug]={};
    ['saisons','films','scans'].forEach(type=>{
      const allCb=document.querySelector(`.cr-all-${pfx}[data-cat="${cat.slug}"][data-type="${type}"]`);
      if(!allCb||allCb.checked){content[cat.slug][type]=[];return;}
      content[cat.slug][type]=[...document.querySelectorAll(`.cr-item-${pfx}[data-cat="${cat.slug}"][data-type="${type}"]:checked`)].map(x=>x.value);
    });
  });
  return{allowed,content};
}

async function saveAccess(){
  const errEl=document.getElementById('ma-err');errEl.style.display='none';
  try{
    const u=allUsers.find(x=>x.username===accessUsername),ep=u?.permissions||{};
    const isAll=document.getElementById('ma-all').checked;
    let allowed=[],content={};
    if(!isAll){const g=_gatherAccess('ma-list');allowed=g.allowed;content=g.content;}
    await api('PUT',`/auth/users/${accessUsername}`,{permissions:{...ep,allowed_catalogues:allowed,catalogue_content:content}});
    toast('Accès mis à jour','ok');cm('m-access');await loadUsers();
  }catch(e){errEl.textContent=typeof e==='string'?e:JSON.stringify(e);errEl.style.display='block';}
}

// ═══════════════════════════ CATALOGUES ══════════════════════════════════
async function loadCats(){
  allCats=await api('GET','/admin/api/catalogues');
  const genres=[...new Set(allCats.flatMap(c=>c.genres||[]))].sort();
  const sel=document.getElementById('cf-genre');
  sel.innerHTML='<option value="">Tous les genres</option>'+genres.map(g=>`<option value="${esc(g)}">${esc(g)}</option>`).join('');
  filterCats();
}
function catVisType(c){const v=c.visibility||{};if(!v.is_public)return'prive';return[v.public_saisons,v.public_films,v.public_scans].some(l=>l?.length)?'partiel':'public';}
function timeAgo(iso){
  if(!iso)return'—';const s=Math.floor((Date.now()-new Date(iso))/1000);
  if(s<60)return'À l\'instant';if(s<3600)return`${Math.floor(s/60)} min`;
  if(s<86400)return`${Math.floor(s/3600)} h`;if(s<86400*7)return`${Math.floor(s/86400)} j`;
  return new Date(iso).toLocaleDateString('fr');
}
function isStale(c){if(c.etat!=='en_cours')return false;if(!c.episodes_synced)return true;return c.updated_at&&(Date.now()-new Date(c.updated_at))>7*86400*1000;}
function filterCats(){
  const q=document.getElementById('cq').value.toLowerCase(),vis=document.getElementById('cf-vis').value;
  const et=document.getElementById('cf-etat').value,sy=document.getElementById('cf-sync').value,gen=document.getElementById('cf-genre').value;
  renderCats(allCats.filter(c=>(!q||(c.nom+c.slug).toLowerCase().includes(q))&&(!vis||catVisType(c)===vis)&&(!et||c.etat===et)&&(!sy||(sy==='yes'?c.episodes_synced:!c.episodes_synced))&&(!gen||(c.genres||[]).includes(gen))));
}
function renderCats(list){
  const b=document.getElementById('ctbody');
  if(!list.length){b.innerHTML=`<tr><td colspan="8"><div class="empty"><div class="ic">📚</div>Aucun catalogue</div></td></tr>`;return;}
  const tl={anime:'🎬 Anime',scan:'📖 Scan',film:'🎞 Film',autre:'📦 Autre'};
  const eb={en_cours:'b-info',termine:'b-ok',abandonne:'b-mu'},el={en_cours:'En cours',termine:'Terminé',abandonne:'Abandonné'};
  b.innerHTML=list.map(c=>{
    const st=isStale(c),bg=bgSyncs.get(c.slug),isSyncing=bg&&!bg.done;
    const nb=[c.saisons.length&&`${c.saisons.length} saison${c.saisons.length>1?'s':''}`,c.films.length&&`${c.films.length} film${c.films.length>1?'s':''}`,c.scans.length&&`${c.scans.length} scan${c.scans.length>1?'s':''}`].filter(Boolean).join(' · ');
    const slug=esc(c.slug);
    return `<tr ${st?'style="background:rgba(245,158,11,.04)"':''}>
      <td style="width:32px;text-align:center"><input type="checkbox" class="ct-sel" value="${slug}" onchange="updateCatBulkBtn()"></td>
      <td>
        <div style="font-weight:600">${esc(c.nom)}</div><div style="font-size:.73rem;color:var(--mu)">${slug}</div>
        ${st?'<span class="badge b-wa" style="margin-top:2px">⚠ MàJ recommandée</span>':''}
        ${isSyncing?`<span class="badge b-info" style="margin-top:2px">${bg.state==='paused'?'⏸ En pause':'⟳ En cours'} ${bg.pct}%</span>`:''}
      </td>
      <td><span class="badge b-mu">${tl[c.type_contenu]||c.type_contenu}</span></td>
      <td style="font-size:.79rem;color:var(--tx2)">${nb||'—'}</td>
      <td><span class="badge ${eb[c.etat]||'b-mu'}">${el[c.etat]||c.etat}</span></td>
      <td><span class="badge ${c.episodes_synced?'b-ok':'b-er'}">${c.episodes_synced?'✓ Oui':'✗ Non'}</span></td>
      <td style="font-size:.78rem;color:var(--mu);white-space:nowrap">${timeAgo(c.updated_at)}</td>
      <td><div class="actions">
        <button class="btn btn-info btn-icon btn-sm"      title="Contenu"     onclick="openContent('${slug}')">👁</button>
        <button class="btn btn-secondary btn-icon btn-sm" title="Modifier"    onclick="openDetail('${slug}')">✏️</button>
        <button class="btn btn-warn btn-icon btn-sm"      title="Rafraîchir"  onclick="doRefresh('${slug}')">↺</button>
        <button class="btn ${isSyncing?'btn-info':'btn-ok'} btn-icon btn-sm"  title="${isSyncing?'Suivre':'Sync'}" onclick="openSync('${slug}')">⟳</button>
        <button class="btn btn-secondary btn-icon btn-sm" title="Visibilité"  onclick="openVis('${slug}')">🔒</button>
        <button class="btn btn-danger btn-icon btn-sm"    title="Supprimer"   onclick="openDeleteCat('${slug}')">🗑</button>
      </div></td>
    </tr>`;
  }).join('');
  updateCatBulkBtn();
}

// ─── Suppression catalogue(s) ────────────────────────────────────────────
function selectAllCats(cb){
  document.querySelectorAll('.ct-sel').forEach(c=>c.checked=cb.checked);
  updateCatBulkBtn();
}
function updateCatBulkBtn(){
  const n=document.querySelectorAll('.ct-sel:checked').length;
  const btn=document.getElementById('bulk-del-btn');
  btn.style.display=n?'':'none';
  document.getElementById('bulk-del-count').textContent=n;
  const allCb=document.getElementById('ct-chk-all');
  const total=document.querySelectorAll('.ct-sel').length;
  if(allCb) allCb.indeterminate=n>0&&n<total,allCb.checked=n===total&&total>0;
}
function openDeleteCat(slug){
  const cat=allCats.find(c=>c.slug===slug);
  _delCatSlugs=[slug];
  document.getElementById('md-text').innerHTML=`Supprimer le catalogue <strong>${esc(cat?.nom||slug)}</strong> ?`;
  om('m-del-cat');
}
function openDeleteSelected(){
  const slugs=[...document.querySelectorAll('.ct-sel:checked')].map(c=>c.value);
  if(!slugs.length){toast('Aucun catalogue sélectionné','wa');return;}
  _delCatSlugs=slugs;
  const names=slugs.map(s=>{const c=allCats.find(x=>x.slug===s);return c?.nom||s;});
  document.getElementById('md-text').innerHTML=`Supprimer ${slugs.length} catalogue${slugs.length>1?'s':''} ?<br><span style="font-size:.8rem;color:var(--mu)">${names.map(n=>`• ${esc(n)}`).join('<br>')}</span>`;
  om('m-del-cat');
}
async function confirmDeleteCats(){
  if(!_delCatSlugs.length)return;
  cm('m-del-cat');
  let ok=0,er=0;
  for(const slug of _delCatSlugs){
    try{await api('DELETE',`/admin/api/catalogues/${slug}`);ok++;}
    catch(e){er++;toast(`Erreur suppression ${slug}: ${e}`,'er');}
  }
  if(ok)toast(`${ok} catalogue${ok>1?'s':''} supprimé${ok>1?'s':''}`, 'ok');
  _delCatSlugs=[];
  await loadCats();
}

// ─── Lecteur vidéo ───────────────────────────────────────────────────────
function openPlayer(videos, title){
  if(!videos?.length){toast('Aucun lecteur disponible','wa');return;}
  _playerVideos=videos;
  document.getElementById('mp-title').textContent=title||'Lecteur';
  const lDiv=document.getElementById('mp-lects');
  if(videos.length>1){
    lDiv.style.display='';
    lDiv.innerHTML='<span class="lbl">Lecteurs :</span>'+videos.map((v,i)=>
      `<button class="btn btn-sm ${i===0?'btn-primary':'btn-secondary'}" onclick="switchPlayer(${i},this)">${esc(v.lecteur||`Lecteur ${i+1}`)}</button>`
    ).join('');
  }else{lDiv.style.display='none';}
  document.getElementById('mp-iframe').src=videos[0].player_url||'';
  om('m-player');
}
function switchPlayer(idx,btn){
  document.querySelectorAll('#mp-lects button').forEach(b=>{b.classList.remove('btn-primary');b.classList.add('btn-secondary');});
  btn.classList.remove('btn-secondary');btn.classList.add('btn-primary');
  document.getElementById('mp-iframe').src=_playerVideos[idx]?.player_url||'';
}
function closePlayer(){
  document.getElementById('mp-iframe').src=''; // stoppe la vidéo
  cm('m-player');
}
// Helpers pour ouvrir le lecteur depuis la vue contenu
function _openEpPlayer(saisonIdx,epNum){
  const s=(_contentData?.saisons||[])[saisonIdx];if(!s)return;
  const ep=(s.episodes||[]).find(e=>e.numero===epNum);if(!ep?.videos?.length)return;
  openPlayer(ep.videos,`${esc(s.nom)} — Ép. ${epNum}`);
}
function _openFilmPlayer(filmIdx){
  const f=(_contentData?.films||[])[filmIdx];if(!f?.videos?.length)return;
  openPlayer(f.videos,esc(f.nom));
}

// ─── Ajouter + recherche ─────────────────────────────────────────────────
function openAddCat(){
  document.getElementById('add-slug').value='';['add-err','add-ok','add-loading','sr-loading'].forEach(i=>document.getElementById(i).style.display='none');
  document.getElementById('sr-results').innerHTML='';document.getElementById('sr-q').value='';document.getElementById('add-btn').disabled=false;om('m-add');
}
async function searchCatalogues(){
  const q=document.getElementById('sr-q').value.trim();if(!q){document.getElementById('sr-results').innerHTML='';return;}
  const btn=document.getElementById('sr-btn'),res=document.getElementById('sr-results'),load=document.getElementById('sr-loading');
  btn.disabled=true;load.style.display='';res.innerHTML='';
  try{
    let combined=[];const found=new Set();
    try{const db=await api('GET',`/catalogues/rechercher?q=${encodeURIComponent(q)}`);(db||[]).forEach(r=>{combined.push(r);found.add(r.slug);});}catch{}
    if(combined.length<5){try{const site=await api('GET',`/catalogues/site/rechercher?q=${encodeURIComponent(q)}`);(site||[]).forEach(r=>{if(!found.has(r.slug)){combined.push(r);found.add(r.slug);}});}catch{}}
    if(!combined.length){res.innerHTML='<p style="color:var(--mu);font-size:.82rem;padding:.4rem 0">Aucun résultat.</p>';return;}
    res.innerHTML=combined.map(r=>`
      <div class="sr-item" onclick="selectSearchResult('${esc(r.slug)}','${esc(r.nom||'')}',this)">
        ${r.image?`<img class="sr-img" src="${esc(r.image)}" onerror="this.style.display='none'" loading="lazy">`:'<div class="sr-img" style="display:flex;align-items:center;justify-content:center;color:var(--mu)">🎬</div>'}
        <div style="flex:1;min-width:0"><div class="sr-nom">${esc(r.nom||r.slug)}</div><div class="sr-slug">${esc(r.slug)}</div>${r.type_contenu?`<span class="badge b-mu" style="margin-top:2px;font-size:.65rem">${esc(r.type_contenu)}</span>`:''}</div>
        <button class="btn btn-primary btn-sm">Sélectionner</button>
      </div>`).join('');
  }finally{btn.disabled=false;load.style.display='none';}
}
function selectSearchResult(slug,nom,el){document.querySelectorAll('.sr-item').forEach(i=>i.classList.remove('selected'));el.classList.add('selected');document.getElementById('add-slug').value=slug;toast(`Slug : ${slug}`,'info');}
async function addCatalogue(){
  const raw=document.getElementById('add-slug').value.trim();const errEl=document.getElementById('add-err'),okEl=document.getElementById('add-ok');errEl.style.display='none';okEl.style.display='none';
  if(!raw){errEl.textContent='Entrez un slug ou sélectionnez un résultat.';errEl.style.display='block';return;}
  let slug=raw;const m=raw.match(/\/catalogue\/([^/]+)/);if(m)slug=m[1];
  document.getElementById('add-btn').disabled=true;document.getElementById('add-loading').style.display='block';
  try{
    const r=await fetch(API+`/catalogues/${slug}`,{headers:{Authorization:`Bearer ${token}`}});
    const d=await r.json().catch(()=>({}));if(!r.ok) throw d.detail||`Erreur ${r.status}`;
    okEl.textContent=`✓ « ${d.nom||slug} » ajouté.`;okEl.style.display='block';toast(`${d.nom||slug} ajouté`,'ok');await loadCats();
  }catch(e){errEl.textContent=typeof e==='string'?e:String(e);errEl.style.display='block';}
  finally{document.getElementById('add-loading').style.display='none';document.getElementById('add-btn').disabled=false;}
}

// ─── Rafraîchir ───────────────────────────────────────────────────────────
async function doRefresh(slug){
  if(!confirm(`Rafraîchir « ${slug} » ?`))return;
  try{toast(`Rafraîchissement de ${slug}…`,'info');await api('POST',`/catalogues/${slug}/rafraichir`);toast(`${slug} rafraîchi`,'ok');await loadCats();}
  catch(e){toast(String(e),'er');}
}

// ─── Détail catalogue ─────────────────────────────────────────────────────
function addTag(field,event){
  if(event.key!=='Enter'&&event.key!==',')return;event.preventDefault();
  const inp=document.getElementById(field==='genres'?'md-gi':'md-li'),val=inp.value.trim().replace(/,$/,'');
  if(!val||detailTags[field].includes(val)){inp.value='';return;}detailTags[field].push(val);renderTags(field);inp.value='';
}
function removeTag(field,idx){detailTags[field].splice(idx,1);renderTags(field);}
function renderTags(field){
  const boxId=field==='genres'?'md-genres-box':'md-langues-box',inpId=field==='genres'?'md-gi':'md-li';
  const box=document.getElementById(boxId),inp=document.getElementById(inpId);
  [...box.querySelectorAll('.etag')].forEach(e=>e.remove());
  detailTags[field].forEach((t,i)=>{const el=document.createElement('span');el.className='etag';el.innerHTML=`${esc(t)}<button onclick="removeTag('${field}',${i})">×</button>`;box.insertBefore(el,inp);});
}
async function openDetail(slug){
  detailSlug=slug;document.getElementById('md-title').textContent=`Modifier — ${slug}`;document.getElementById('md-err').style.display='none';
  try{
    const d=await api('GET',`/admin/api/catalogues/${slug}`);
    document.getElementById('md-slug').value=d.slug||'';document.getElementById('md-url').value=d.url||'';
    document.getElementById('md-nom').value=d.nom||'';document.getElementById('md-alt').value=d.titre_alternatif||'';
    document.getElementById('md-syn').value=d.synopsis||'';document.getElementById('md-etat').value=d.etat||'en_cours';document.getElementById('md-type').value=d.type_contenu||'anime';
    document.getElementById('md-created').textContent=d.created_at?new Date(d.created_at).toLocaleDateString('fr'):'—';
    document.getElementById('md-updated').textContent=d.updated_at?new Date(d.updated_at).toLocaleString('fr'):'—';
    detailTags.genres=[...(d.genres||[])];detailTags.langues=[...(d.langues||[])];renderTags('genres');renderTags('langues');om('m-detail');
  }catch(e){toast(String(e),'er');}
}
async function saveDetail(){
  const errEl=document.getElementById('md-err');errEl.style.display='none';
  try{
    await api('PUT',`/admin/api/catalogues/${detailSlug}`,{nom:document.getElementById('md-nom').value.trim()||undefined,titre_alternatif:document.getElementById('md-alt').value.trim()||undefined,synopsis:document.getElementById('md-syn').value.trim()||undefined,etat:document.getElementById('md-etat').value,type_contenu:document.getElementById('md-type').value,genres:detailTags.genres,langues:detailTags.langues});
    toast('Catalogue mis à jour','ok');cm('m-detail');await loadCats();
  }catch(e){errEl.textContent=typeof e==='string'?e:JSON.stringify(e);errEl.style.display='block';}
}

// ─── Viewer contenu ───────────────────────────────────────────────────────
async function openContent(slug){
  const cat=allCats.find(c=>c.slug===slug)||{nom:slug};
  document.getElementById('mc-title').textContent=`Contenu — ${cat.nom}`;document.getElementById('mc-sync-badge').textContent='';
  document.getElementById('mc-body').innerHTML='<div class="empty"><div class="ic">⏳</div>Chargement…</div>';om('m-content');
  try{
    const d=await api('GET',`/admin/api/catalogues/${slug}/contenu`);
    _contentData=d;
    const sb=document.getElementById('mc-sync-badge');
    if(d.episodes_synced){sb.textContent='✓ Synchronisé';sb.className='badge b-ok';}else{sb.textContent='✗ Non synchronisé';sb.className='badge b-er';}
    renderContentView(d);
  }catch(e){document.getElementById('mc-body').innerHTML=`<div class="empty"><div class="ic">⚠</div>${esc(String(e))}</div>`;}
}
function renderContentView(d){
  const ns=d.saisons.length,nf=d.films.length,nsc=d.scans.length;
  document.getElementById('mc-body').innerHTML=`
    <div class="ctabs">
      <div class="ctab active" onclick="showCTab(this,'ct-saisons')">🎬 Saisons (${ns})</div>
      <div class="ctab" onclick="showCTab(this,'ct-films')">🎞 Films (${nf})</div>
      <div class="ctab" onclick="showCTab(this,'ct-scans')">📖 Scans (${nsc})</div>
    </div>
    <div id="ct-saisons" class="ctab-content active">${renderSaisonsContent(d.saisons)}</div>
    <div id="ct-films"   class="ctab-content">${renderFilmsContent(d.films)}</div>
    <div id="ct-scans"  class="ctab-content">${renderScansContent(d.scans)}</div>`;
}
function showCTab(el,id){document.querySelectorAll('.ctab').forEach(t=>t.classList.remove('active'));document.querySelectorAll('.ctab-content').forEach(t=>t.classList.remove('active'));el.classList.add('active');document.getElementById(id).classList.add('active');}
function renderSaisonsContent(saisons){
  if(!saisons.length) return '<div class="empty"><div class="ic">🎬</div>Aucune saison</div>';
  return saisons.map((s,idx)=>{
    const hasEps=s.episodes.length>0,langBadge=s.lang?`<span class="badge b-mu" style="font-size:.65rem">${esc(s.lang.toUpperCase())}</span>`:'';
    return `<div class="citem"><div class="citem-head" onclick="toggleCItem('sei-${idx}')"><span class="ci-nom">${esc(s.nom)}</span>${langBadge}<span class="ci-count">${hasEps?`${s.episodes.length} éps`:(s.total_episodes?`${s.total_episodes} éps (non chargés)`:'Aucun épisode')}</span><span style="color:var(--mu);margin-left:.4rem">▾</span></div>
    <div class="citem-body ${hasEps?'':'unsynced'}" id="sei-${idx}">${hasEps?renderEpChips(s.episodes,'ep',idx):'<p style="margin:0">⚠ Épisodes non synchronisés.</p>'}</div></div>`;
  }).join('');
}
function renderFilmsContent(films){
  if(!films.length) return '<div class="empty"><div class="ic">🎞</div>Aucun film</div>';
  return films.map((f,idx)=>{
    const hasVids=(f.videos||[]).length>0,langBadge=f.lang?`<span class="badge b-mu" style="font-size:.65rem">${esc(f.lang.toUpperCase())}</span>`:'';
    const pillsHtml=hasVids
      ?'<div style="margin-top:.35rem">'+f.videos.map((v,i)=>
          `<span class="lecteur-pill playable" onclick="_openFilmPlayer(${idx})" title="Ouvrir ${esc(v.lecteur||'lecteur')}" data-lidx="${i}">▶ ${esc(v.lecteur||`Lecteur ${i+1}`)}</span>`
        ).join('')+'</div>'
      :'<p style="margin:0">⚠ Vidéos non synchronisées.</p>';
    return `<div class="citem"><div class="citem-head" onclick="toggleCItem('fi-${idx}')"><span class="ci-nom">${esc(f.nom)}</span>${langBadge}<span class="ci-count">${hasVids?`${f.videos_count} lecteur(s)`:'Non synchronisé'}</span><span style="color:var(--mu);margin-left:.4rem">▾</span></div>
    <div class="citem-body ${hasVids?'':'unsynced'}" id="fi-${idx}">${pillsHtml}</div></div>`;
  }).join('');
}
function renderScansContent(scans){
  if(!scans.length) return '<div class="empty"><div class="ic">📖</div>Aucun scan</div>';
  return scans.map((sc,idx)=>{
    const hasChaps=sc.chapitres.length>0,langBadge=sc.lang?`<span class="badge b-mu" style="font-size:.65rem">${esc(sc.lang.toUpperCase())}</span>`:'';
    return `<div class="citem"><div class="citem-head" onclick="toggleCItem('sci-${idx}')"><span class="ci-nom">${esc(sc.nom)}</span>${langBadge}<span class="ci-count">${hasChaps?`${sc.total_chapitres} chapitres`:'Non synchronisé'}</span><span style="color:var(--mu);margin-left:.4rem">▾</span></div>
    <div class="citem-body ${hasChaps?'':'unsynced'}" id="sci-${idx}">${hasChaps?renderEpChips(sc.chapitres,'chap'):'<p style="margin:0">⚠ Chapitres non synchronisés.</p>'}</div></div>`;
  }).join('');
}
function renderEpChips(items,cls,saisonIdx){
  const MAX=120;
  const chip=e=>{
    const play=e.videos&&e.videos.length>0;
    const attr=play?`onclick="_openEpPlayer(${saisonIdx},${e.numero})" title="Lire — ${e.videos.length} lecteur(s)"`:'';
    return `<span class="ep-chip ${cls}${play?' playable':''}" ${attr}>${e.numero}</span>`;
  };
  const chips=items.slice(0,MAX).map(chip).join('');
  const more=items.length>MAX?`<span class="ep-more" onclick="this.outerHTML='${items.slice(MAX).map(e=>`<span class=\\"ep-chip ${cls}\\">${e.numero}</span>`).join('')}'">… +${items.length-MAX} de plus</span>`:'';
  return `<div class="ep-grid">${chips}${more}</div>`;
}
function toggleCItem(id){document.getElementById(id).classList.toggle('open');}

// ─── Visibilité ────────────────────────────────────────────────────────────
function openVis(slug){
  visSlug=slug;const cat=allCats.find(c=>c.slug===slug);
  const v=cat.visibility||{is_public:true,public_saisons:[],public_films:[],public_scans:[]};
  document.getElementById('mv-title').textContent=`Visibilité — ${cat.nom}`;
  const sec=(key,label,items)=>{if(!items?.length)return'';const al=v['public_'+key]||[],ia=al.length===0;
    return `<div class="cs" style="margin-bottom:.65rem"><label>${label}</label><div class="pills"><label class="pill"><input type="checkbox" id="va-${key}" ${ia?'checked':''} onchange="onVisAll('${key}')">✓ Tous</label>${items.map(i=>`<label class="pill"><input type="checkbox" class="vi" data-type="${key}" value="${esc(i.slug)}" ${(ia||al.includes(i.slug))?'checked':''}>${esc(i.nom||i.slug)}${i.lang?` <span style="opacity:.55">(${i.lang})</span>`:''}</label>`).join('')}</div></div>`;};
  document.getElementById('mv-body').innerHTML=`
    <div class="fg" style="margin-bottom:.75rem">
      <label class="fsw"><input type="checkbox" id="vp" ${v.is_public!==false?'checked':''} onchange="document.getElementById('vc').style.display=this.checked?'':'none'"><span style="font-weight:600">Catalogue accessible publiquement</span></label>
    </div>
    <div id="vc" ${v.is_public===false?'style="display:none"':''}>
      <p style="font-size:.76rem;color:var(--mu);margin-bottom:.6rem">Contenu visible sans authentification (vide = tout).</p>
      ${sec('saisons','🎬 Saisons',cat.saisons)}${sec('films','🎞 Films',cat.films)}${sec('scans','📖 Scans',cat.scans)}
    </div>`;
  om('m-vis');
}
function onVisAll(type){const c=document.getElementById('va-'+type).checked;document.querySelectorAll(`.vi[data-type="${type}"]`).forEach(i=>i.checked=c);}
async function saveVisibility(){
  const ip=document.getElementById('vp').checked;
  const gi=type=>{const a=document.getElementById('va-'+type);if(!ip||!a||a.checked)return[];return[...document.querySelectorAll(`.vi[data-type="${type}"]:checked`)].map(x=>x.value);};
  try{await api('PUT',`/admin/api/catalogues/${visSlug}/visibility`,{is_public:ip,public_saisons:gi('saisons'),public_films:gi('films'),public_scans:gi('scans')});toast('Visibilité mise à jour','ok');cm('m-vis');await loadCats();}
  catch(e){toast(String(e),'er');}
}

// ═══════════════════════════════ SYNC ═════════════════════════════════════
const STATE_LABELS={starting:'Démarrage…',running:'En cours',paused:'En pause',cancelling:'Annulation…',cancelled:'Annulé',done:'Terminé',error:'Erreur'};
const STATE_BADGES={starting:'b-info',running:'b-info',paused:'b-wa',cancelling:'b-er',cancelled:'b-mu',done:'b-ok',error:'b-er'};
const BAR_CLS={paused:'paused',done:'done',error:'er',cancelled:'cancelled',cancelling:'er'};

// FIX barre de progression : connexion directe en WS sans passer par HTTP POST.
// Le serveur s'abonne AVANT de créer la tâche → aucun événement n'est manqué.
async function openSync(slug){
  const existing=bgSyncs.get(slug);
  if(existing&&!existing.done){
    // Sync déjà en cours : ouvrir le modal et reconnecter si besoin
    activeSyncSlug=slug;renderSyncModal(slug);om('m-sync');
    if(!existing.ws||existing.ws.readyState>1) connectSyncWS(slug);
    return;
  }
  const state={ws:null,events:[],pct:0,total:0,done_items:0,state:'starting',currentItem:'',done:false};
  bgSyncs.set(slug,state);activeSyncSlug=slug;renderSyncModal(slug);om('m-sync');
  connectSyncWS(slug);
}

function connectSyncWS(slug){
  const state=bgSyncs.get(slug);if(state.ws){try{state.ws.close();}catch{}}
  const ws=new WebSocket(`${WS_API}/catalogues/${slug}/sync-content/ws?token=${encodeURIComponent(token)}`);
  state.ws=ws;
  ws.onmessage=e=>{try{onSyncEvent(slug,JSON.parse(e.data));}catch{}};
  ws.onerror=()=>{if(!state.done){state.state='error';state.done=true;updateBgBar();if(activeSyncSlug===slug)renderSyncModal(slug);}};
  ws.onclose=()=>{if(!state.done){updateBgBar();if(activeSyncSlug===slug)renderSyncModal(slug);}};
}

function onSyncEvent(slug,ev){
  const s=bgSyncs.get(slug);if(!s)return;
  switch(ev.type){
    case 'started':s.state='running';addSyncLog(slug,'▶ Démarrage…','run');break;
    case 'progress_init':s.total=(ev.nb_saisons||0)+(ev.nb_films||0)+(ev.nb_scans||0);addSyncLog(slug,`ℹ ${ev.nb_saisons||0} saison(s) · ${ev.nb_films||0} film(s) · ${ev.nb_scans||0} scan(s)`,'run');break;
    case 'saison_start':case 'film_start':case 'scan_start':s.currentItem=ev.nom||ev.slug||'';addSyncLog(slug,`  ⟳ ${s.currentItem}…`,'run');break;
    case 'saison_done':s.done_items++;s.pct=pctCalc(s);addSyncLog(slug,`  ✓ ${ev.nom} — ${ev.episodes_count??'?'} épisodes`,'ok');break;
    case 'film_done':s.done_items++;s.pct=pctCalc(s);addSyncLog(slug,`  ✓ ${ev.nom} (film)`,'ok');break;
    case 'scan_done':s.done_items++;s.pct=pctCalc(s);addSyncLog(slug,`  ✓ ${ev.nom} — ${ev.chapitres_count??'?'} chapitres`,'ok');break;
    case 'saison_skip':case 'film_skip':case 'scan_skip':s.done_items++;s.pct=pctCalc(s);addSyncLog(slug,`  ↷ ${ev.nom} (déjà sync.)`,'skip');break;
    case 'saison_error':case 'film_error':case 'scan_error':s.done_items++;s.pct=pctCalc(s);addSyncLog(slug,`  ✕ ${ev.nom} — erreur`,'er');break;
    case 'paused':s.state='paused';addSyncLog(slug,'⏸ '+ev.message,'pause');break;
    case 'resumed':s.state='running';addSyncLog(slug,'▶ Reprise…','run');break;
    case 'cancelling':s.state='cancelling';addSyncLog(slug,'⚠ '+ev.message,'cancel');break;
    case 'cancelled':s.state='cancelled';s.done=true;addSyncLog(slug,'✕ Annulé.','cancel');loadCats();break;
    case 'completed':s.state='done';s.pct=100;s.done=true;addSyncLog(slug,`✓ Terminé — ${ev.total_episodes??''} éps`,'ok');loadCats();break;
    case 'error':s.state='error';s.done=true;addSyncLog(slug,`✕ ${ev.message||ev.reason||'Erreur'}`,'er');break;
    case 'info':addSyncLog(slug,`ℹ ${ev.message||''}`,'run');break;
  }
  updateBgBar();if(activeSyncSlug===slug)renderSyncModal(slug);
}
function pctCalc(s){return s.total>0?Math.round(s.done_items/s.total*100):0;}
function addSyncLog(slug,text,cls=''){
  const s=bgSyncs.get(slug);if(s)s.events.push({text,cls});
  if(activeSyncSlug===slug){const log=document.getElementById('ms-log');if(log){const el=document.createElement('div');el.className=`sl-${cls==='ok'?'ok':cls==='skip'?'skip':cls==='er'?'er':cls==='pause'?'pause':cls==='cancel'?'cancel':'run'}`;el.textContent=text;log.appendChild(el);log.scrollTop=log.scrollHeight;}}
}
function renderSyncModal(slug){
  const s=bgSyncs.get(slug);if(!s)return;const st=s.state,done=s.done;
  document.getElementById('ms-title').textContent=`Synchronisation — ${slug}`;
  const badge=document.getElementById('ms-state-badge');badge.textContent=STATE_LABELS[st]||st;badge.className=`badge ${STATE_BADGES[st]||'b-mu'}`;
  document.getElementById('ms-label').textContent=done?STATE_LABELS[st]:(s.currentItem?`En cours : ${s.currentItem}`:STATE_LABELS[st]);
  document.getElementById('ms-pct').textContent=s.pct+'%';
  const bar=document.getElementById('ms-bar');bar.style.width=s.pct+'%';bar.className='prog-fill '+(BAR_CLS[st]||'');
  const $=id=>document.getElementById(id);
  $('ms-btn-pause').style.display=(!done&&st==='running')?'':'none';
  $('ms-btn-resume').style.display=(!done&&st==='paused')?'':'none';
  $('ms-btn-cancel').style.display=(!done&&st!=='cancelling')?'':'none';$('ms-btn-cancel').disabled=st==='cancelling';
  $('ms-btn-fond').style.display=!done?'':'none';$('ms-btn-close').style.display=done?'':'none';
  const log=document.getElementById('ms-log');
  if(log&&log.children.length===0&&s.events.length>0){s.events.forEach(ev=>{const el=document.createElement('div');el.className=`sl-${ev.cls==='ok'?'ok':ev.cls==='skip'?'skip':ev.cls==='er'?'er':ev.cls==='pause'?'pause':ev.cls==='cancel'?'cancel':'run'}`;el.textContent=ev.text;log.appendChild(el);});log.scrollTop=log.scrollHeight;}
}
async function syncPause(){if(activeSyncSlug)try{await api('POST',`/catalogues/${activeSyncSlug}/sync-content/pause`);}catch(e){toast(String(e),'er');}}
async function syncResume(){if(activeSyncSlug)try{await api('POST',`/catalogues/${activeSyncSlug}/sync-content/resume`);}catch(e){toast(String(e),'er');}}
async function syncCancel(){if(!activeSyncSlug||!confirm('Annuler ?'))return;try{await api('DELETE',`/catalogues/${activeSyncSlug}/sync-content`);}catch(e){toast(String(e),'er');}}
function syncFond(){cm('m-sync');activeSyncSlug=null;toast('Sync en arrière-plan','info');}
function updateBgBar(){
  const active=[...bgSyncs.entries()].filter(([,s])=>!s.done);
  const badge=document.getElementById('sync-badge');badge.textContent=active.length?`⟳ ${active.length} sync en cours`:'';badge.style.display=active.length?'':'none';
  const bar=document.getElementById('bg-bar'),list=document.getElementById('bg-list');
  if(!active.length){if(bar)bar.style.display='none';return;}if(bar)bar.style.display='block';
  if(list)list.innerHTML=active.map(([slug,s])=>{const ip=s.state==='paused';
    return `<div class="bg-item"><span class="badge ${STATE_BADGES[s.state]||'b-mu'}" style="font-size:.65rem">${STATE_LABELS[s.state]||s.state}</span><span class="bi-slug">${esc(slug)}</span><div class="mini-prog"><div class="mini-fill ${ip?'paused':''}" style="width:${s.pct}%"></div></div><span class="bi-pct">${s.pct}%</span>
    <button class="btn btn-info btn-sm" onclick="openSync('${esc(slug)}')">Suivre</button>
    <button class="btn btn-warn btn-sm" onclick="${ip?`bgResume('${esc(slug)}')`:`bgPause('${esc(slug)}')`}">${ip?'▶':'⏸'}</button>
    <button class="btn btn-danger btn-sm" onclick="bgCancel('${esc(slug)}')">✕</button></div>`;
  }).join('');
  filterCats();
}
async function bgPause(slug){try{await api('POST',`/catalogues/${slug}/sync-content/pause`);}catch(e){toast(String(e),'er');}}
async function bgResume(slug){try{await api('POST',`/catalogues/${slug}/sync-content/resume`);}catch(e){toast(String(e),'er');}}
async function bgCancel(slug){if(!confirm(`Annuler sync « ${slug} » ?`))return;try{await api('DELETE',`/catalogues/${slug}/sync-content`);}catch(e){toast(String(e),'er');}}

// ═══════════════════════════ APPLICATIONS ════════════════════════════════

async function loadApps(){allClients=await api('GET','/admin/api/clients');filterApps();}

function filterApps(){
  const q=document.getElementById('aq').value.toLowerCase(),st=document.getElementById('af-status').value;
  renderApps(allClients.filter(c=>(!q||c.name.toLowerCase().includes(q))&&(!st||(st==='active'?c.is_active:!c.is_active))));
}

function renderApps(list){
  const b=document.getElementById('atbody');
  if(!list.length){b.innerHTML=`<tr><td colspan="6"><div class="empty"><div class="ic">🔌</div>Aucune application</div></td></tr>`;return;}
  b.innerHTML=list.map(c=>{
    const p=c.permissions||{},cats=p.allowed_catalogues||[],blk=c.is_blocked,q=p.quota||{};
    const quotaInfo=q.enabled?`<span class="quota-used">Quota: ${q.max_syncs}/${q.period==='day'?'j':q.period==='year'?'an':'mois'}</span>`:'';
    return `<tr>
      <td><div style="display:flex;align-items:center;gap:.55rem">
        <div class="avc">${esc(c.name).slice(0,2).toUpperCase()}</div>
        <div><div style="font-weight:600">${esc(c.name)}</div>${c.description?`<div style="font-size:.72rem;color:var(--mu)">${esc(c.description)}</div>`:''}</div>
      </div></td>
      <td><span class="mono" style="font-size:.72rem">${esc(c.client_id)}</span></td>
      <td>
        <span class="badge ${c.is_active?'b-ok':'b-er'}">${c.is_active?'Actif':'Inactif'}</span>
        ${blk?'<span class="badge b-block" style="margin-left:3px">🚫 Bloqué</span>':''}
      </td>
      <td><div style="display:flex;gap:.2rem;flex-wrap:wrap"><span class="pc ${p.can_sync?'on':''}">⟳ Sync</span><span class="pc ${p.can_delete?'on':''}">🗑 Suppr</span><span class="pc ${p.can_refresh?'on':''}">↺ Refresh</span>${quotaInfo}</div></td>
      <td>${cats.length===0?'<span class="badge b-info">Tous</span>':cats.slice(0,3).map(s=>`<span class="tag">${esc(s)}</span>`).join('')+(cats.length>3?`<span class="tag">+${cats.length-3}</span>`:'')}</td>
      <td><div class="actions">
        <button class="btn btn-secondary btn-icon btn-sm" title="Modifier"          onclick="openEditClient('${esc(c.client_id)}')">✏️</button>
        <button class="btn btn-secondary btn-icon btn-sm" title="Accès catalogues"  onclick="openClientAccess('${esc(c.client_id)}')">🔑</button>
        <button class="btn btn-warn btn-icon btn-sm"      title="Régénérer secret"  onclick="regenerateSecret('${esc(c.client_id)}')">🔄</button>
        <button class="btn ${blk?'btn-ok':'btn-danger'} btn-icon btn-sm" title="${blk?'Débloquer':'Bloquer'}" onclick="${blk?`unblock('client','${esc(c.client_id)}')`:`openBlock('client','${esc(c.client_id)}')`}">${blk?'✓':'🚫'}</button>
        <button class="btn btn-danger btn-icon btn-sm"   title="Supprimer"          onclick="deleteClient('${esc(c.client_id)}')">🗑</button>
      </div></td>
    </tr>`;
  }).join('');
}

function openCreateClient(){
  editClientId=null;document.getElementById('mc2-title').textContent='Nouvelle application';
  document.getElementById('mc2-name').value='';document.getElementById('mc2-desc').value='';
  document.getElementById('mc2-active').checked=true;
  ['mc2-sync','mc2-del','mc2-ref'].forEach(i=>document.getElementById(i).checked=false);
  document.getElementById('mc2-err').style.display='none';om('m-client');
}
function openEditClient(cid){
  editClientId=cid;const c=allClients.find(x=>x.client_id===cid);
  document.getElementById('mc2-title').textContent=`Modifier — ${c.name}`;
  document.getElementById('mc2-name').value=c.name||'';document.getElementById('mc2-desc').value=c.description||'';
  document.getElementById('mc2-active').checked=c.is_active;
  const p=c.permissions||{};document.getElementById('mc2-sync').checked=!!p.can_sync;document.getElementById('mc2-del').checked=!!p.can_delete;document.getElementById('mc2-ref').checked=!!p.can_refresh;
  // Quota
  const q=p.quota||{};const qen=document.getElementById('mc2-q-en');qen.checked=!!q.enabled;
  document.getElementById('mc2-q-max').value=q.max_syncs||10;document.getElementById('mc2-q-period').value=q.period||'month';
  document.getElementById('mc2-quota-fields').style.display=q.enabled?'flex':'none';
  // Blocage
  if(c.is_blocked){const bb=document.createElement('div');bb.id='mc2-blocked-banner';bb.className='blocked-banner';bb.innerHTML=`🚫 Cette application est actuellement bloquée${c.blocked_reason?' ('+esc(c.blocked_reason)+')':''}`;const bd=document.getElementById('m-client').querySelector('.mbd');const ex=document.getElementById('mc2-blocked-banner');if(ex)ex.remove();bd.insertBefore(bb,bd.firstChild);}else{const ex=document.getElementById('mc2-blocked-banner');if(ex)ex.remove();}
  document.getElementById('mc2-err').style.display='none';om('m-client');
}
async function saveClient(){
  const errEl=document.getElementById('mc2-err');errEl.style.display='none';
  const name=document.getElementById('mc2-name').value.trim();if(!name){errEl.textContent='Le nom est requis.';errEl.style.display='block';return;}
  const qen2=document.getElementById('mc2-q-en').checked;
  const quota2={enabled:qen2,period:document.getElementById('mc2-q-period').value,max_syncs:parseInt(document.getElementById('mc2-q-max').value)||10};
  const perms={can_sync:document.getElementById('mc2-sync').checked,can_delete:document.getElementById('mc2-del').checked,can_refresh:document.getElementById('mc2-ref').checked,quota:quota2};
  try{
    if(editClientId){
      const ex=allClients.find(c=>c.client_id===editClientId)?.permissions||{};
      perms.allowed_catalogues=ex.allowed_catalogues||[];perms.catalogue_content=ex.catalogue_content||{};
      await api('PUT',`/admin/api/clients/${editClientId}`,{name,description:document.getElementById('mc2-desc').value.trim()||null,is_active:document.getElementById('mc2-active').checked,permissions:perms});
      toast('Application mise à jour','ok');cm('m-client');await loadApps();
    }else{
      const r=await api('POST','/admin/api/clients',{name,description:document.getElementById('mc2-desc').value.trim()||null,permissions:perms});
      cm('m-client');showSecretModal(r.client_id,r.client_secret,true);
    }
  }catch(e){errEl.textContent=typeof e==='string'?e:JSON.stringify(e);errEl.style.display='block';}
}
async function deleteClient(cid){
  const c=allClients.find(x=>x.client_id===cid);if(!confirm(`Supprimer « ${c?.name||cid} » ?`))return;
  try{await api('DELETE',`/admin/api/clients/${cid}`);toast('Application supprimée','ok');await loadApps();}
  catch(e){toast(String(e),'er');}
}
async function regenerateSecret(cid){
  if(!confirm('Régénérer le secret ? L\'ancien secret sera immédiatement révoqué.'))return;
  try{const r=await api('POST',`/admin/api/clients/${cid}/regenerate-secret`);showSecretModal(r.client_id,r.client_secret,false);}
  catch(e){toast(String(e),'er');}
}
function showSecretModal(cid,secret,isNew){
  document.getElementById('ms2-title').textContent=isNew?'Application créée — Secret':'Secret régénéré';
  document.getElementById('ms2-cid').textContent=cid;
  document.getElementById('ms2-secret').textContent=secret;
  om('m-secret');
}

// ─── Quota UI toggle ─────────────────────────────────────────────────────
function toggleQuotaUI(pfx){
  const en=document.getElementById(pfx+'-q-en').checked;
  document.getElementById(pfx+'-quota-fields').style.display=en?'flex':'none';
}

// ─── Blocage ──────────────────────────────────────────────────────────────
let _blockTarget=null; // {type:'user'|'client', id: username|client_id}

function openBlock(type,id){
  _blockTarget={type,id};
  document.getElementById('mb-title').textContent=type==='user'?`Bloquer @${id}`:`Bloquer ${id}`;
  document.getElementById('mb-reason').value='';document.getElementById('mb-until').value='';
  document.getElementById('mb-err').style.display='none';om('m-block');
}
async function saveBlock(){
  if(!_blockTarget)return;
  const errEl=document.getElementById('mb-err');errEl.style.display='none';
  const reason=document.getElementById('mb-reason').value.trim()||null;
  const until=document.getElementById('mb-until').value;
  const blockedUntil=until?new Date(until).toISOString():null;
  const body={is_blocked:true,blocked_reason:reason,blocked_until:blockedUntil};
  try{
    if(_blockTarget.type==='user'){await api('PUT',`/auth/users/${_blockTarget.id}`,body);}
    else{await api('PUT',`/admin/api/clients/${_blockTarget.id}`,body);}
    toast(`${_blockTarget.id} bloqué`,'wa');cm('m-block');
    if(_blockTarget.type==='user')await loadUsers();else await loadApps();
  }catch(e){errEl.textContent=typeof e==='string'?e:JSON.stringify(e);errEl.style.display='block';}
}
async function unblock(type,id){
  if(!confirm(`Débloquer « ${id} » ?`))return;
  const body={is_blocked:false,blocked_reason:null,blocked_until:null};
  try{
    if(type==='user'){await api('PUT',`/auth/users/${id}`,body);await loadUsers();}
    else{await api('PUT',`/admin/api/clients/${id}`,body);await loadApps();}
    toast(`${id} débloqué`,'ok');
  }catch(e){toast(String(e),'er');}
}

// ─── Accès catalogues Clients ─────────────────────────────────────────────
function openClientAccess(cid){
  cltAccessClientId=cid;const c=allClients.find(x=>x.client_id===cid);
  document.getElementById('mca-title').textContent=`Accès catalogues — ${c?.name||cid}`;document.getElementById('mca-err').style.display='none';
  const p=c?.permissions||{},allowed=p.allowed_catalogues||[];
  document.getElementById('mca-all').checked=allowed.length===0;
  renderAccessList('mca-list','mca-all',allowed,p.catalogue_content||{});om('m-clt-access');
}
function toggleAllCatsClt(){document.getElementById('mca-list').style.display=document.getElementById('mca-all').checked?'none':'';}
async function saveClientAccess(){
  const errEl=document.getElementById('mca-err');errEl.style.display='none';
  try{
    const c=allClients.find(x=>x.client_id===cltAccessClientId),ep=c?.permissions||{};
    const isAll=document.getElementById('mca-all').checked;
    let allowed=[],content={};
    if(!isAll){const g=_gatherAccess('mca-list');allowed=g.allowed;content=g.content;}
    await api('PUT',`/admin/api/clients/${cltAccessClientId}`,{permissions:{...ep,allowed_catalogues:allowed,catalogue_content:content}});
    toast('Accès mis à jour','ok');cm('m-clt-access');await loadApps();
  }catch(e){errEl.textContent=typeof e==='string'?e:JSON.stringify(e);errEl.style.display='block';}
}

// ═══════════════════════ GROUPES ═════════════════════════════════════════

let editGroupId=null, membersGroupId=null;
let _allGenres=[], _mgCatSlugs=new Set(), _mgGenres=new Set();

const GROUP_TYPE_LABELS={catalogue:'🗂️ Catalogues',genre:'🏷️ Genres',permission:'🔐 Permissions'};
const GROUP_TYPE_CLS   ={catalogue:'gt-catalogue',genre:'gt-genre',permission:'gt-permission'};

async function loadGroups(){
  try{
    allGroups=await api('GET','/admin/api/groups');
    filterGroups();
    // Pré-charger les genres pour le modal
    _allGenres=await api('GET','/admin/api/genres');
  }catch(e){toast(String(e),'er');}
}

function filterGroups(){
  const q=document.getElementById('gq').value.toLowerCase();
  const t=document.getElementById('gf-type').value;
  renderGroups(allGroups.filter(g=>(!q||g.name.toLowerCase().includes(q))&&(!t||g.type===t)));
}

function renderGroups(list){
  const b=document.getElementById('gtbody');
  if(!list.length){b.innerHTML=`<tr><td colspan="6"><div class="empty"><div class="ic">🏷️</div>Aucun groupe</div></td></tr>`;return;}
  b.innerHTML=list.map(g=>{
    const p=g.permissions||{};
    const perms=[];
    if(p.can_sync)   perms.push('<span class="badge b-ok" style="font-size:.68rem">Sync</span>');
    if(p.can_delete) perms.push('<span class="badge b-er" style="font-size:.68rem">Suppr.</span>');
    if(p.can_refresh)perms.push('<span class="badge b-info" style="font-size:.68rem">Refresh</span>');
    const q2=p.quota||{};if(q2.enabled)perms.push(`<span class="badge" style="font-size:.68rem;background:var(--sur2)">Quota:${q2.max_syncs}/${q2.period}</span>`);

    let detail='—';
    if(g.type==='catalogue')detail=`${(g.catalogue_slugs||[]).length} catalogue(s)`;
    else if(g.type==='genre')detail=(g.genres||[]).map(x=>`<span class="genre-chip" style="cursor:default">${esc(x)}</span>`).join('') || '—';

    return `<tr>
      <td><span style="font-weight:600">${esc(g.name)}</span>${g.description?`<div style="font-size:.72rem;color:var(--mu)">${esc(g.description)}</div>`:''}</td>
      <td><span class="gt-badge ${GROUP_TYPE_CLS[g.type]||''}">${GROUP_TYPE_LABELS[g.type]||g.type}</span></td>
      <td style="font-size:.78rem">${detail}</td>
      <td>
        <button class="btn btn-secondary btn-sm" style="gap:.3rem" onclick="openMembers('${esc(g.id)}','${esc(g.name)}')">
          👤 ${g.member_count??0}
        </button>
      </td>
      <td style="font-size:.78rem">${perms.join(' ') || '<span style="color:var(--mu)">—</span>'}</td>
      <td><div class="actions">
        <button class="btn btn-secondary btn-icon btn-sm" title="Modifier" onclick="openEditGroup('${esc(g.id)}')">✏️</button>
        <button class="btn btn-danger btn-icon btn-sm"   title="Supprimer" onclick="deleteGroup('${esc(g.id)}','${esc(g.name)}')">🗑</button>
      </div></td>
    </tr>`;
  }).join('');
}

function onGroupTypeChange(){
  const t=document.getElementById('mg-type').value;
  document.getElementById('mg-sect-catalogue').style.display=t==='catalogue'?'':'none';
  document.getElementById('mg-sect-genre').style.display=t==='genre'?'':'none';
}

// ── Catalogues chips ──────────────────────────────────────────────────────
function _mgRenderCatChips(){
  const el=document.getElementById('mg-cat-chips');
  el.innerHTML=[..._mgCatSlugs].map(s=>`<span class="genre-chip">${esc(s)}<button onclick="event.stopPropagation();_mgCatSlugs.delete('${esc(s)}');_mgRenderCatChips()">✕</button></span>`).join('')||'<span style="color:var(--mu);font-size:.75rem">Aucun catalogue sélectionné</span>';
}

let _mgCatSearchTimer=null;
async function mgSearchCats(){
  clearTimeout(_mgCatSearchTimer);
  const q=document.getElementById('mg-cat-search').value.trim();
  const drop=document.getElementById('mg-cat-drop');
  if(!q||q.length<2){drop.style.display='none';return;}
  _mgCatSearchTimer=setTimeout(async()=>{
    drop.innerHTML=`<div class="sd-empty">Recherche…</div>`;drop.style.display='';
    try{
      let res=[];
      // Chercher d'abord en DB
      try{res=await api('GET','/catalogues/rechercher?q='+encodeURIComponent(q));}catch{}
      // Si peu de résultats, compléter avec ce qu'on a en mémoire
      if(!res.length){res=allCats.filter(c=>(c.nom||'').toLowerCase().includes(q.toLowerCase())).slice(0,8);}
      if(!res.length){drop.innerHTML=`<div class="sd-empty">Aucun résultat — <a href="#" onclick="mgSiteSearch('${esc(q)}');return false" style="color:var(--ac)">chercher sur le site</a></div>`;return;}
      drop.innerHTML=res.slice(0,10).map(r=>{
        const slug=r.slug||'';const nom=r.nom||r.title||slug;
        const already=_mgCatSlugs.has(slug)?'opacity:.5;pointer-events:none':'';
        return `<div class="sd-item" style="${already}" onclick="mgSelectCat('${esc(slug)}','${esc(nom)}')">
          <span>${esc(nom)}</span><span class="sd-slug">${esc(slug)}</span>
        </div>`;
      }).join('');
    }catch(e){drop.innerHTML=`<div class="sd-empty">${esc(String(e))}</div>`;}
  },280);
}
async function mgSiteSearch(q){
  const drop=document.getElementById('mg-cat-drop');
  drop.innerHTML=`<div class="sd-empty">Recherche sur le site…</div>`;
  try{
    const res=await api('GET','/catalogues/site/rechercher?q='+encodeURIComponent(q));
    if(!res.length){drop.innerHTML=`<div class="sd-empty">Aucun résultat</div>`;return;}
    drop.innerHTML=res.slice(0,10).map(r=>{
      const slug=r.slug||'';const nom=r.title||r.nom||slug;
      return `<div class="sd-item" onclick="mgSelectCat('${esc(slug)}','${esc(nom)}')">
        <span>${esc(nom)}</span><span class="sd-slug">${esc(slug)}</span>
      </div>`;
    }).join('');
  }catch{drop.innerHTML=`<div class="sd-empty">Erreur de recherche</div>`;}
}
function mgSelectCat(slug,name){
  _mgCatSlugs.add(slug);_mgRenderCatChips();
  document.getElementById('mg-cat-search').value='';
  document.getElementById('mg-cat-drop').style.display='none';
}
// Fermer le dropdown en cliquant ailleurs
document.addEventListener('click',e=>{
  if(!e.target.closest('.mg-cat-search-wrap')){
    const d=document.getElementById('mg-cat-drop');if(d)d.style.display='none';
  }
});

// ── Genres grid ────────────────────────────────────────────────────────────
function renderGenreGrid(){
  const q=(document.getElementById('mg-genre-filter')?.value||'').toLowerCase();
  const el=document.getElementById('mg-genre-grid');
  if(!_allGenres.length){el.innerHTML=`<span style="color:var(--mu);font-size:.78rem">Aucun genre disponible — cliquez sur ↺ Sync genres</span>`;return;}
  const filtered=q?_allGenres.filter(g=>g.toLowerCase().includes(q)):_allGenres;
  if(!filtered.length){el.innerHTML=`<span style="color:var(--mu);font-size:.78rem">Aucun genre correspondant</span>`;return;}
  el.innerHTML=filtered.map(g=>`<span class="gs-chip ${_mgGenres.has(g)?'on':''}" onclick="toggleGenreChip('${esc(g)}')">${esc(g)}</span>`).join('');
}
function filterGenreGrid(){renderGenreGrid();}
function toggleGenreChip(g){
  if(_mgGenres.has(g))_mgGenres.delete(g);else _mgGenres.add(g);
  renderGenreGrid();
}
async function syncGenres(){
  const btn=document.getElementById('mg-genre-sync-btn');
  const lbl=document.getElementById('mg-genre-sync-lbl');
  btn.disabled=true;btn.textContent='⏳ En cours…';lbl.textContent='';
  try{
    await api('POST','/admin/api/genres/sync');
    lbl.textContent='Synchronisation lancée…';
    // Recharger après 4s (le scraping est en arrière-plan)
    setTimeout(async()=>{
      _allGenres=await api('GET','/admin/api/genres').catch(()=>_allGenres);
      renderGenreGrid();lbl.textContent=`${_allGenres.length} genres`;
      btn.disabled=false;btn.textContent='↺ Sync genres';
    },4000);
  }catch(e){lbl.textContent=String(e);btn.disabled=false;btn.textContent='↺ Sync genres';}
}

function _populateGroupModal(){
  _mgRenderCatChips();
  renderGenreGrid();
  onGroupTypeChange();
  // Mettre à jour l'info de la dernière sync dans le label
  const lbl=document.getElementById('mg-genre-sync-lbl');
  if(lbl)lbl.textContent=_allGenres.length?`${_allGenres.length} genres en DB`:'Aucun genre en DB — lancez une sync';
}

function openCreateGroup(){
  editGroupId=null;_mgCatSlugs=new Set();_mgGenres=new Set();
  document.getElementById('mg-title').textContent='Nouveau groupe';
  document.getElementById('mg-name').value='';document.getElementById('mg-desc').value='';
  document.getElementById('mg-type').value='catalogue';
  document.getElementById('mg-sync').checked=false;document.getElementById('mg-del').checked=false;document.getElementById('mg-ref').checked=false;
  document.getElementById('mg-q-en').checked=false;document.getElementById('mg-q-max').value=10;document.getElementById('mg-q-period').value='month';
  document.getElementById('mg-quota-fields').style.display='none';
  document.getElementById('mg-err').style.display='none';
  _populateGroupModal();om('m-group');
}
function openEditGroup(gid){
  const g=allGroups.find(x=>x.id===gid);if(!g)return;
  editGroupId=gid;
  _mgCatSlugs=new Set(g.catalogue_slugs||[]);
  _mgGenres=new Set(g.genres||[]);
  document.getElementById('mg-title').textContent=`Modifier — ${g.name}`;
  document.getElementById('mg-name').value=g.name;
  document.getElementById('mg-desc').value=g.description||'';
  document.getElementById('mg-type').value=g.type||'catalogue';
  const p=g.permissions||{};
  document.getElementById('mg-sync').checked=!!p.can_sync;
  document.getElementById('mg-del').checked=!!p.can_delete;
  document.getElementById('mg-ref').checked=!!p.can_refresh;
  const q=p.quota||{};
  document.getElementById('mg-q-en').checked=!!q.enabled;
  document.getElementById('mg-q-max').value=q.max_syncs||10;
  document.getElementById('mg-q-period').value=q.period||'month';
  document.getElementById('mg-quota-fields').style.display=q.enabled?'flex':'none';
  document.getElementById('mg-err').style.display='none';
  _populateGroupModal();om('m-group');
}
async function saveGroup(){
  const errEl=document.getElementById('mg-err');errEl.style.display='none';
  const name=document.getElementById('mg-name').value.trim();
  if(!name){errEl.textContent='Le nom est requis.';errEl.style.display='block';return;}
  const type=document.getElementById('mg-type').value;
  const qen=document.getElementById('mg-q-en').checked;
  const body={
    name,type,description:document.getElementById('mg-desc').value.trim()||null,
    catalogue_slugs:[..._mgCatSlugs],genres:[..._mgGenres],
    permissions:{
      can_sync:document.getElementById('mg-sync').checked,
      can_delete:document.getElementById('mg-del').checked,
      can_refresh:document.getElementById('mg-ref').checked,
      quota:{enabled:qen,period:document.getElementById('mg-q-period').value,max_syncs:parseInt(document.getElementById('mg-q-max').value)||10},
    },
  };
  try{
    if(editGroupId){await api('PUT',`/admin/api/groups/${editGroupId}`,body);toast('Groupe mis à jour','ok');}
    else{await api('POST','/admin/api/groups',body);toast('Groupe créé','ok');}
    cm('m-group');await loadGroups();
  }catch(e){errEl.textContent=typeof e==='string'?e:JSON.stringify(e);errEl.style.display='block';}
}
async function deleteGroup(gid,name){
  if(!confirm(`Supprimer le groupe « ${name} » ? Les membres seront retirés du groupe.`))return;
  try{await api('DELETE',`/admin/api/groups/${gid}`);toast('Groupe supprimé','ok');await loadGroups();}
  catch(e){toast(String(e),'er');}
}

// ── Membres du groupe ──────────────────────────────────────────────────────
async function openMembers(gid,name){
  membersGroupId=gid;
  document.getElementById('mm-title').textContent=`Membres — ${name}`;
  // Remplir la datalist des utilisateurs
  const dl=document.getElementById('mm-users-dl');
  dl.innerHTML=allUsers.map(u=>`<option value="${esc(u.username)}">`).join('');
  document.getElementById('mm-add-u').value='';
  await refreshMembersList();om('m-members');
}
async function refreshMembersList(){
  try{
    const members=await api('GET',`/admin/api/groups/${membersGroupId}/members`);
    const b=document.getElementById('mm-body');
    if(!members.length){b.innerHTML=`<div class="empty" style="padding:.85rem"><div class="ic">👥</div>Aucun membre</div>`;return;}
    b.innerHTML=`<table class="dt"><thead><tr><th>Utilisateur</th><th>Email</th><th>Rôle</th><th></th></tr></thead><tbody>${
      members.map(m=>`<tr>
        <td style="font-weight:600">${esc(m.username)}</td>
        <td style="font-size:.8rem;color:var(--mu)">${esc(m.email||'—')}</td>
        <td><span class="badge ${m.role==='admin'?'b-ac':'b-mu'}">${esc(m.role)}</span></td>
        <td><button class="btn btn-danger btn-icon btn-sm" title="Retirer" onclick="removeGroupMember('${esc(m.username)}')">✕</button></td>
      </tr>`).join('')
    }</tbody></table>`;
  }catch(e){toast(String(e),'er');}
}
async function addGroupMember(){
  const u=document.getElementById('mm-add-u').value.trim();if(!u)return;
  try{await api('POST',`/admin/api/groups/${membersGroupId}/members`,{username:u});
    document.getElementById('mm-add-u').value='';toast(`${u} ajouté`,'ok');await refreshMembersList();}
  catch(e){toast(String(e),'er');}
}
async function removeGroupMember(username){
  if(!confirm(`Retirer ${username} du groupe ?`))return;
  try{await api('DELETE',`/admin/api/groups/${membersGroupId}/members/${username}`);toast(`${username} retiré`,'ok');await refreshMembersList();}
  catch(e){toast(String(e),'er');}
}

// ═══════════════════════ SORTIES SEMAINE (anime-sama.to/planning/) ═══════

let _planningData=[];

const JOURS_FR=['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'];

async function loadPlanning(){
  const grid=document.getElementById('planning-grid');
  const errEl=document.getElementById('planning-err');
  grid.innerHTML='<div style="grid-column:1/-1"><div class="empty"><div class="ic">⏳</div>Chargement du planning…</div></div>';
  errEl.style.display='none';
  try{
    _planningData=await api('GET','/planning/');
    await renderPlanning();
  }catch(e){
    grid.innerHTML='';errEl.textContent='Impossible de récupérer le planning : '+String(e);errEl.style.display='block';
  }
}

async function renderPlanning(){
  const grid=document.getElementById('planning-grid');
  if(!_planningData||!_planningData.length){
    grid.innerHTML='<div style="grid-column:1/-1"><div class="empty"><div class="ic">📭</div>Aucune donnée disponible pour cette semaine.</div></div>';return;
  }
  // Enrichir avec les slugs connus en DB
  const dbSlugs=new Set(allCats.map(c=>c.slug));
  const today=new Date();const todayDay=today.toLocaleDateString('fr-FR',{weekday:'long'}).charAt(0).toUpperCase()+today.toLocaleDateString('fr-FR',{weekday:'long'}).slice(1);
  grid.innerHTML=_planningData.map(day=>{
    const isToday=day.jour===todayDay;
    const animes=day.animes||[];
    const animesHtml=animes.length?animes.map(a=>{
      const inDb=dbSlugs.has(a.slug);
      const langCls=a.lang?'lang-'+a.lang.replace(/[^a-z]/gi,'').toLowerCase():'';
      const thumb=a.image?`<img class="anime-thumb" src="${esc(a.image)}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`:'';
      const ph=`<div class="anime-thumb-ph" ${a.image?'style="display:none"':''}">🎬</div>`;
      return `<div class="anime-card ${inDb?'in-db':''}" title="${esc(a.titre)}${a.saison_info?' — '+esc(a.saison_info):''}">
        ${thumb}${ph}
        <div class="anime-info">
          <div class="anime-titre">${esc(a.titre)}</div>
          <div class="anime-sub">${esc(a.saison_info||'')}</div>
          <div style="display:flex;align-items:center;gap:.25rem;margin-top:.1rem">
            ${a.heure?`<span class="anime-heure">${esc(a.heure)}</span>`:''}
            ${a.lang?`<span class="lang-badge ${langCls}">${esc(a.lang)}</span>`:''}
          </div>
        </div>
        <div class="anime-actions">
          ${inDb?`<button class="btn btn-secondary btn-icon btn-sm" title="Voir dans les catalogues" onclick="switchToSlug('${esc(a.slug)}')">📚</button>`
                :`<button class="btn btn-primary btn-icon btn-sm" title="Ajouter au catalogue" onclick="openAddCatWithSlug('${esc(a.slug)}','${esc(a.titre)}')">+</button>`}
        </div>
      </div>`;
    }).join(''):`<div class="no-anime">Aucune sortie</div>`;
    return `<div class="day-col ${isToday?'today':''}">
      <div class="day-hd"><div class="dnom">${esc(day.jour)}</div><div class="ddate">${esc(day.date||'')}</div></div>
      <div class="day-animes">${animesHtml}</div>
    </div>`;
  }).join('');
}

function switchToSlug(slug){
  // Basculer sur l'onglet catalogues et filtrer par slug
  const el=document.querySelector('.ni[data-tab="catalogues"]');if(el)switchTab(el);
  setTimeout(()=>{const qi=document.getElementById('cq');if(qi){qi.value=slug;filterCats();}},100);
}

function openAddCatWithSlug(slug,titre){
  openAddCat();
  setTimeout(()=>{
    const si=document.getElementById('mc-slug');const ti=document.getElementById('mc-title-search');
    if(si){si.value=slug;}
    if(ti){ti.value=titre;}
  },80);
}

// ═══════════════════════ PLANIFICATION ══════════════════════════════════

let allSchedules=[], allHistory=[], editScheduleId=null;

const FREQ_LABELS={daily:'Quotidien',weekly:'Hebdomadaire',biweekly:'Bi-hebdomadaire',monthly:'Mensuel',custom:'Personnalisé'};
const DAYS=['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'];

function freqLabel(s){
  const h=String(s.hour||0).padStart(2,'0'),m2=String(s.minute||0).padStart(2,'0'),t=`${h}h${m2}`;
  switch(s.frequency){
    case 'daily':   return `Quotidien à ${t} UTC`;
    case 'weekly':  return `Chaque ${DAYS[s.day_of_week||0]} à ${t} UTC`;
    case 'biweekly':return `Toutes les 2 sem. (${DAYS[s.day_of_week||0]}) à ${t} UTC`;
    case 'monthly': return `Mensuel le ${s.day_of_month||1} à ${t} UTC`;
    case 'custom':  return `Tous les ${s.interval_days||7} j. à ${t} UTC`;
    default:return s.frequency;
  }
}

function fmtDuration(s){if(!s)return'—';if(s<60)return`${s}s`;if(s<3600)return`${Math.floor(s/60)}m ${s%60}s`;return`${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`;}

async function loadSchedules(){
  try{allSchedules=await api('GET','/admin/api/schedules');renderSchedules();}
  catch(e){toast(String(e),'er');}
}
function renderSchedules(){
  const b=document.getElementById('stbody');
  if(!allSchedules.length){b.innerHTML=`<tr><td colspan="6"><div class="empty"><div class="ic">📅</div>Aucune programmation</div></td></tr>`;return;}
  b.innerHTML=allSchedules.map(s=>{
    const next=s.next_run?new Date(s.next_run).toLocaleString('fr'):'—';
    const last=s.last_run?new Date(s.last_run).toLocaleString('fr'):'Jamais';
    return `<tr>
      <td><div style="font-weight:600">${esc(s.slug)}</div>${s.description?`<div style="font-size:.72rem;color:var(--mu)">${esc(s.description)}</div>`:''}</td>
      <td style="font-size:.82rem">${esc(freqLabel(s))}</td>
      <td style="font-size:.78rem;color:var(--info)">${next}</td>
      <td style="font-size:.78rem;color:var(--mu)">${last}</td>
      <td><span class="badge ${s.active?'b-ok':'b-mu'}">${s.active?'Actif':'Inactif'}</span></td>
      <td><div class="actions">
        <button class="btn btn-ok btn-icon btn-sm"       title="Lancer maintenant" onclick="runScheduleNow('${esc(s.id)}','${esc(s.slug)}')">▶</button>
        <button class="btn btn-secondary btn-icon btn-sm" title="Modifier"          onclick="openEditSchedule('${esc(s.id)}')">✏️</button>
        <button class="btn btn-warn btn-icon btn-sm"      title="${s.active?'Désactiver':'Activer'}" onclick="toggleSchedule('${esc(s.id)}',${!s.active})">${s.active?'⏸':'▶'}</button>
        <button class="btn btn-danger btn-icon btn-sm"    title="Supprimer"         onclick="deleteSchedule('${esc(s.id)}')">🗑</button>
      </div></td>
    </tr>`;
  }).join('');
}

function onFreqChange(){
  const freq=document.getElementById('ms3-freq').value;
  document.getElementById('ms3-dow-field').style.display=['weekly','biweekly'].includes(freq)?'block':'none';
  document.getElementById('ms3-dom-field').style.display=freq==='monthly'?'block':'none';
  document.getElementById('ms3-interval-field').style.display=freq==='custom'?'block':'none';
}

function openCreateSchedule(){
  editScheduleId=null;document.getElementById('ms3-title').textContent='Nouvelle programmation';
  document.getElementById('ms3-slug').value='';document.getElementById('ms3-desc').value='';
  document.getElementById('ms3-freq').value='weekly';document.getElementById('ms3-hour').value='2';document.getElementById('ms3-min').value='0';
  document.getElementById('ms3-dow').value='0';document.getElementById('ms3-dom').value='1';document.getElementById('ms3-interval').value='7';
  document.getElementById('ms3-active').checked=true;document.getElementById('ms3-err').style.display='none';
  // Alimenter la datalist
  const dl=document.getElementById('ms3-cat-list');dl.innerHTML=allCats.map(c=>`<option value="${esc(c.slug)}">${esc(c.nom)}</option>`).join('');
  onFreqChange();om('m-schedule');
}
function openEditSchedule(sid){
  const s=allSchedules.find(x=>x.id===sid);if(!s)return;
  editScheduleId=sid;document.getElementById('ms3-title').textContent=`Modifier — ${s.slug}`;
  document.getElementById('ms3-slug').value=s.slug;document.getElementById('ms3-desc').value=s.description||'';
  document.getElementById('ms3-freq').value=s.frequency||'daily';document.getElementById('ms3-hour').value=s.hour??2;document.getElementById('ms3-min').value=s.minute??0;
  document.getElementById('ms3-dow').value=s.day_of_week??0;document.getElementById('ms3-dom').value=s.day_of_month??1;document.getElementById('ms3-interval').value=s.interval_days??7;
  document.getElementById('ms3-active').checked=s.active!==false;document.getElementById('ms3-err').style.display='none';
  const dl=document.getElementById('ms3-cat-list');dl.innerHTML=allCats.map(c=>`<option value="${esc(c.slug)}">${esc(c.nom)}</option>`).join('');
  onFreqChange();om('m-schedule');
}
async function saveSchedule(){
  const errEl=document.getElementById('ms3-err');errEl.style.display='none';
  const freq=document.getElementById('ms3-freq').value,slug=document.getElementById('ms3-slug').value.trim();
  if(!slug){errEl.textContent='Le slug est requis.';errEl.style.display='block';return;}
  const body={slug,description:document.getElementById('ms3-desc').value.trim()||null,frequency:freq,hour:parseInt(document.getElementById('ms3-hour').value)||0,minute:parseInt(document.getElementById('ms3-min').value)||0,active:document.getElementById('ms3-active').checked};
  if(['weekly','biweekly'].includes(freq)) body.day_of_week=parseInt(document.getElementById('ms3-dow').value);
  if(freq==='monthly') body.day_of_month=parseInt(document.getElementById('ms3-dom').value)||1;
  if(freq==='custom') body.interval_days=parseInt(document.getElementById('ms3-interval').value)||7;
  try{
    if(editScheduleId){await api('PUT',`/admin/api/schedules/${editScheduleId}`,body);toast('Programmation mise à jour','ok');}
    else{await api('POST','/admin/api/schedules',body);toast('Programmation créée','ok');}
    cm('m-schedule');await loadSchedules();
  }catch(e){errEl.textContent=typeof e==='string'?e:JSON.stringify(e);errEl.style.display='block';}
}
async function deleteSchedule(sid){
  if(!confirm('Supprimer cette programmation ?'))return;
  try{await api('DELETE',`/admin/api/schedules/${sid}`);toast('Supprimé','ok');await loadSchedules();}
  catch(e){toast(String(e),'er');}
}
async function toggleSchedule(sid,active){
  try{await api('PUT',`/admin/api/schedules/${sid}`,{active});await loadSchedules();}
  catch(e){toast(String(e),'er');}
}
async function runScheduleNow(sid,slug){
  if(!confirm(`Lancer la sync de « ${slug} » maintenant ?`))return;
  try{
    await api('POST',`/admin/api/schedules/${sid}/run`);
    toast(`Sync de ${slug} démarrée`,'ok');
    // Ouvrir le modal de suivi
    await openSync(slug);
  }catch(e){toast(String(e),'er');}
}

// ─── Historique ───────────────────────────────────────────────────────────
async function loadHistory(){
  try{allHistory=await api('GET','/admin/api/history');filterHistory();}
  catch(e){toast(String(e),'er');}
}
function filterHistory(){
  const q=document.getElementById('hq').value.toLowerCase(),st=document.getElementById('hf-status').value,tr=document.getElementById('hf-trig').value;
  const list=allHistory.filter(h=>(!q||h.slug.includes(q))&&(!st||h.status===st)&&(!tr||(tr==='schedule'?h.triggered_by.startsWith('schedule'):!h.triggered_by.startsWith('schedule'))));
  renderHistory(list);
}
// ═══════════════════════ RECHERCHE AVANCÉE ═══════════════════════════════════

let _srPage=0, _srKnownSlugs=new Set(), _srAllGenres=[], _srSelGenres=new Set(), _srInitDone=false;

async function initSearch(){
  if(_srInitDone)return;
  _srInitDone=true;
  try{_srAllGenres=await api('GET','/admin/api/genres');}catch{_srAllGenres=[];}
  try{const cats=await api('GET','/admin/api/catalogues');_srKnownSlugs=new Set((cats||[]).map(c=>c.slug));}catch{}
  renderSearchGenreGrid();
  document.getElementById('sr-empty').style.display='flex';
}

function renderSearchGenreGrid(){
  const q=(document.getElementById('sf-genre-filter')?.value||'').toLowerCase();
  const filtered=_srAllGenres.filter(g=>!q||g.toLowerCase().includes(q));
  const el=document.getElementById('sf-genre-grid');
  if(!el)return;
  if(!filtered.length){el.innerHTML='<span style="color:var(--mu);font-size:.78rem;padding:.4rem">Aucun genre</span>';return;}
  el.innerHTML=filtered.map(g=>`<span class="gs-chip ${_srSelGenres.has(g)?'on':''}" onclick="toggleSearchGenre('${esc(g)}')">${esc(g)}</span>`).join('');
  const cnt=document.getElementById('sf-genre-count');
  if(cnt)cnt.textContent=_srSelGenres.size?`(${_srSelGenres.size} sél.)` :'';
}

function filterSearchGenres(){renderSearchGenreGrid();}

function toggleSearchGenre(g){
  if(_srSelGenres.has(g))_srSelGenres.delete(g);else _srSelGenres.add(g);
  renderSearchGenreGrid();
}

function _sfChecked(cls){return [...document.querySelectorAll(`.${cls}:checked`)].map(i=>i.value);}

function clearSearchFilters(){
  const sfQ=document.getElementById('sf-q');if(sfQ)sfQ.value='';
  const sfGF=document.getElementById('sf-genre-filter');if(sfGF)sfGF.value='';
  const sfAMin=document.getElementById('sf-annee-min');if(sfAMin)sfAMin.value='';
  const sfAMax=document.getElementById('sf-annee-max');if(sfAMax)sfAMax.value='';
  document.querySelectorAll('.sf-type,.sf-langue,.sf-statut').forEach(cb=>cb.checked=false);
  _srSelGenres.clear();_srPage=0;
  renderSearchGenreGrid();
  document.getElementById('sr-grid').innerHTML='';
  document.getElementById('sr-more').style.display='none';
  document.getElementById('sr-status').style.display='none';
  document.getElementById('sr-empty').innerHTML='<div class="ic">🔍</div>Utilisez les filtres pour rechercher des catalogues sur anime-sama.to';
  document.getElementById('sr-empty').style.display='flex';
}

async function runSearch(page=1){
  const search=document.getElementById('sf-q')?.value.trim()||'';
  const types=_sfChecked('sf-type');
  const langues=_sfChecked('sf-langue');
  const statuts=_sfChecked('sf-statut');
  const genres=[..._srSelGenres];
  const anneeMin=document.getElementById('sf-annee-min')?.value||'';
  const anneeMax=document.getElementById('sf-annee-max')?.value||'';

  const p=new URLSearchParams();
  p.set('page',page);
  if(search)p.set('search',search);
  if(types.length)p.set('type',types.join(','));
  if(langues.length)p.set('langue',langues.join(','));
  if(statuts.length)p.set('statut',statuts.join(','));
  if(genres.length)p.set('genre',genres.join(','));
  if(anneeMin)p.set('annee_min',anneeMin);
  if(anneeMax)p.set('annee_max',anneeMax);

  const statusEl=document.getElementById('sr-status');
  const gridEl=document.getElementById('sr-grid');
  const emptyEl=document.getElementById('sr-empty');
  const moreEl=document.getElementById('sr-more');
  const moreBtn=document.getElementById('sr-more-btn');

  emptyEl.style.display='none';
  statusEl.innerHTML='<span style="display:inline-flex;align-items:center;gap:.4rem"><span style="display:inline-block;width:13px;height:13px;border:2px solid var(--bdr);border-top-color:var(--ac);border-radius:50%;animation:spin .6s linear infinite"></span> Recherche sur anime-sama.to…</span>';
  statusEl.style.display='';
  if(page===1){gridEl.innerHTML='';moreEl.style.display='none';}
  if(moreBtn)moreBtn.disabled=true;

  try{
    try{const cats=await api('GET','/admin/api/catalogues');_srKnownSlugs=new Set((cats||[]).map(c=>c.slug));}catch{}

    let results;
    try{results=await api('GET',`/catalogues/site/rechercher?${p}`);}
    catch(e){
      if(String(e).includes('404')||String(e).includes('Aucun')){results=[];}
      else throw e;
    }
    const list=Array.isArray(results)?results:[];

    if(page===1&&!list.length){
      statusEl.style.display='none';
      emptyEl.innerHTML='<div class="ic">😶</div>Aucun résultat pour ces critères';
      emptyEl.style.display='flex';
      return;
    }

    gridEl.insertAdjacentHTML('beforeend',list.map(r=>_srCard(r)).join(''));
    _srPage=page;
    statusEl.textContent=page===1?`${list.length} résultat${list.length>1?'s':''}`:`+${list.length} résultats (page ${page})`;
    moreEl.style.display=list.length>=18?'':'none';
  }catch(e){
    statusEl.textContent=`❌ ${String(e)}`;
  }finally{
    if(moreBtn)moreBtn.disabled=false;
  }
}

function _srCard(r){
  const inDb=_srKnownSlugs.has(r.slug);
  const img=r.image
    ?`<img class="src-poster" src="${esc(r.image)}" loading="lazy" onerror="this.outerHTML='<div class=src-poster-ph>🎬</div>'">`
    :`<div class="src-poster-ph">🎬</div>`;
  const tb=r.type_contenu?`<span class="badge b-mu" style="font-size:.62rem">${esc(r.type_contenu)}</span>`:'';
  const db=inDb?`<span class="badge" style="background:rgba(16,185,129,.15);color:#6ee7b7;border:1px solid rgba(16,185,129,.3);font-size:.62rem">✓ En base</span>`:'';
  const addBtn=inDb
    ?`<button class="btn btn-secondary btn-sm" style="font-size:.7rem;padding:.2rem .5rem;pointer-events:none" disabled>✓ Ajouté</button>`
    :`<button class="btn btn-primary btn-sm" style="font-size:.7rem;padding:.2rem .5rem" onclick="addFromSearch('${esc(r.slug)}','${esc(r.nom||'')}',this)">+ Ajouter</button>`;
  return `<div class="src-card${inDb?' in-db':''}" data-slug="${esc(r.slug)}">
    ${img}
    <div class="src-info">
      <div class="src-nom">${esc(r.nom||r.slug)}</div>
      <div class="src-slug">${esc(r.slug)}</div>
      <div style="display:flex;gap:.25rem;flex-wrap:wrap;margin-top:.2rem">${tb}${db}</div>
    </div>
    <div class="src-foot">${addBtn}</div>
  </div>`;
}

async function addFromSearch(slug,titre,btn){
  btn.disabled=true;btn.textContent='⏳';
  try{
    const r=await fetch(API+`/catalogues/${slug}`,{headers:{Authorization:`Bearer ${token}`}});
    const d=await r.json().catch(()=>({}));
    if(!r.ok)throw d.detail||`Erreur ${r.status}`;
    toast(`${d.nom||slug} ajouté`,'ok');
    _srKnownSlugs.add(slug);
    const card=document.querySelector(`.src-card[data-slug="${slug}"]`);
    if(card){
      card.classList.add('in-db');
      const foot=card.querySelector('.src-foot');
      if(foot)foot.innerHTML=`<button class="btn btn-secondary btn-sm" style="font-size:.7rem;padding:.2rem .5rem" disabled>✓ Ajouté</button>`;
      const infoLast=card.querySelector('.src-info>div:last-child');
      if(infoLast)infoLast.insertAdjacentHTML('beforeend',`<span class="badge" style="background:rgba(16,185,129,.15);color:#6ee7b7;border:1px solid rgba(16,185,129,.3);font-size:.62rem">✓ En base</span>`);
    }
    loadCats();
  }catch(e){
    toast(String(e),'er');
    btn.disabled=false;btn.textContent='+ Ajouter';
  }
}

// Ajout animation spinner
const _srStyle=document.createElement('style');
_srStyle.textContent='@keyframes spin{to{transform:rotate(360deg)}}';
document.head.appendChild(_srStyle);

// ══════════════════════════════════════════════════════════════════════════════

function renderHistory(list){
  const b=document.getElementById('htbody');
  if(!list.length){b.innerHTML=`<tr><td colspan="6"><div class="empty"><div class="ic">🕒</div>Aucune sync enregistrée</div></td></tr>`;return;}
  const scls={completed:'sc-completed',cancelled:'sc-cancelled',error:'sc-error'};
  const slbl={completed:'✓ Terminé',cancelled:'↷ Annulé',error:'✕ Erreur'};
  b.innerHTML=list.map(h=>{
    const by=h.triggered_by||'';
    const byLabel=by.startsWith('schedule:')?`📅 ${by.split(':')[1]||'auto'}`:(by?`👤 ${by}`:'Manuel');
    const started=h.started_at?new Date(h.started_at).toLocaleString('fr'):'—';
    return `<tr>
      <td><span style="font-weight:600;font-family:monospace;font-size:.82rem">${esc(h.slug)}</span></td>
      <td style="font-size:.78rem;color:var(--mu)">${esc(byLabel)}</td>
      <td style="font-size:.78rem;color:var(--mu);white-space:nowrap">${started}</td>
      <td style="font-size:.78rem">${fmtDuration(h.duration_s)}</td>
      <td><span class="status-chip ${scls[h.status]||''}">${slbl[h.status]||h.status}</span></td>
      <td style="font-size:.78rem;color:var(--mu)">${h.total_items??'—'} éléments</td>
    </tr>`;
  }).join('');
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def admin_ui():
    return HTMLResponse(_HTML.replace("__API_BASE__", API_BASE))


if __name__ == "__main__":
    print(f"  Interface admin : http://localhost:{ADMIN_PORT}")
    print(f"  API principale  : {API_BASE}")
    uvicorn.run("admin_main:app", host="0.0.0.0", port=ADMIN_PORT, reload=True)
