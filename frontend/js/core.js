// Ported from the original KoforLink demo; HTTP transport is in api.js.

function safeStorageGet(k){ try { return localStorage.getItem(k); } catch (e) { return null; } }

function safeStorageSet(k, v){ try { localStorage.setItem(k, v); return true; } catch (e) { return false; } }

function safeStorageRemove(k){ try { localStorage.removeItem(k); return true; } catch (e) { return false; } }

function __kfShowError(msg){
  try {
    if (State.ready) return;
    var boot = document.getElementById('bootScreen');
    if (boot) boot.style.display = 'none';
    var es = document.getElementById('errorScreen');
    if (es) {
      es.classList.remove('hidden');
      var m = document.getElementById('errorScreenMessage');
      if (m && msg) m.textContent = msg;
    }
  } catch (e) {}
}

window.onerror = function(message, source, lineno, colno, error){
  console.error('[KoforLink] Uncaught error:', message, source + ':' + lineno + ':' + colno, error);
  __kfShowError('An unexpected error occurred. Please try again.');
  return false;
};

window.addEventListener('unhandledrejection', function(ev){
  console.error('[KoforLink] Unhandled promise rejection:', ev.reason);
});

function hideBoot(){
  try { var b = document.getElementById('bootScreen'); if (b && b.parentNode) b.parentNode.removeChild(b); } catch (e) {}
}

const State = {
  user: null,
  settings: {},
  counts: { notifications:0, messages:0, connectionRequests:0 },
  profilePhoto: '',
  isStaff: false,
  isAdmin: false,
  emailVerified: false,
  pendingEmail: '',
  feed: { posts: [], offset: 0, hasMore: true, loading: false },
  currentChat: null,
  chatPoll: null,
  theme: safeStorageGet('kf_theme') || 'system',
  stories: [],
  storyTimer: null,
  storyElapsed: 0,
  storyIndex: 0,
  storyGroup: null,
  cache: {}
};

const $ = function(sel, root){ return (root||document).querySelector(sel); };

const $$ = function(sel, root){ return Array.prototype.slice.call((root||document).querySelectorAll(sel)); };

function esc(s){
  return String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function initials(name){
  var p = String(name||'?').trim().split(/\s+/);
  var a = (p[0]||'?').charAt(0), b = p[1] ? p[1].charAt(0) : '';
  return (a + b).toUpperCase();
}

function avatar(url, name, size){
  size = size || '40';
  var cls = 'avatar avatar-' + size;
  if (url) return '<div class="' + cls + '"><img src="' + esc(url) + '" alt="" onerror="this.parentNode.innerHTML=\'' + esc(initials(name)) + '\'"></div>';
  return '<div class="' + cls + '">' + esc(initials(name)) + '</div>';
}

function timeAgo(iso){
  if (!iso) return '';
  var d = new Date(iso); if (isNaN(d)) return '';
  var s = Math.floor((Date.now()-d.getTime())/1000);
  if (s<60) return 'just now';
  var m = Math.floor(s/60); if (m<60) return m+'m';
  var h = Math.floor(m/60); if (h<24) return h+'h';
  var day = Math.floor(h/24); if (day<7) return day+'d';
  var w = Math.floor(day/7); if (w<5) return w+'w';
  var mo = Math.floor(day/30); if (mo<12) return mo+'mo';
  return Math.floor(day/365)+'y';
}

function fmtDate(iso){
  if (!iso) return '';
  var d = new Date(iso); if (isNaN(d)) return iso;
  return d.toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});
}

function debounce(fn, ms){
  ms = ms || 300;
  var t; return function(){ var a = arguments, ctx = this; clearTimeout(t); t = setTimeout(function(){ fn.apply(ctx, a); }, ms); };
}

function verifiedBadge(){
  return '<span class="verified-badge" title="Verified"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></span>';
}

function toast(msg, type){
  type = type || 'success';
  var icons = {
    success:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>',
    error:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>',
    warn:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.7 3.86a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>'
  };
  var root = document.getElementById('toasts'); if (!root) return;
  var el = document.createElement('div');
  el.className = 'toast ' + type;
  el.innerHTML = (icons[type]||icons.success) + '<div>' + esc(msg) + '</div>';
  root.appendChild(el);
  setTimeout(function(){ el.style.animation='toastIn .3s reverse'; setTimeout(function(){ el.remove(); }, 280); }, 3600);
}

function openModal(opts){
  opts = opts || {};
  var title = opts.title, body = opts.body, footer = opts.footer, size = opts.size || '';
  var wrap = document.createElement('div');
  wrap.className = 'overlay';
  wrap.setAttribute('role','dialog');
  wrap.setAttribute('aria-modal','true');
  wrap.innerHTML =
    '<div class="modal ' + size + '">' +
      (title ? '<div class="modal-head"><h2>' + esc(title) + '</h2>' +
        '<button type="button" class="icon-btn" data-close aria-label="Close">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg></button></div>' : '') +
      '<div class="modal-body">' + (body||'') + '</div>' +
      (footer ? '<div class="modal-foot">' + footer + '</div>' : '') +
    '</div>';
  wrap.addEventListener('click', function(e){
    if (e.target === wrap) { closeModal(wrap); return; }
    var btn = e.target.closest('[data-close]');
    if (btn) { closeModal(wrap); return; }
  });
  $('#modalRoot').appendChild(wrap);
  // ESC closes the top-most modal (but not while a story viewer is open).
  if (!wrap._escBound) {
    wrap._escBound = true;
    document.addEventListener('keydown', function onEsc(e){
      if (e.key === 'Escape') {
        if (document.querySelector('.story-viewer')) return;
        if (document.body.contains(wrap)) closeModal(wrap);
        document.removeEventListener('keydown', onEsc);
      }
    });
  }
  return wrap;
}

function closeModal(el){
  if (el && el.parentNode) {
    try { el.style.animation = 'fadeIn .2s reverse'; } catch (e) {}
    setTimeout(function(){ if (el.parentNode) el.remove(); }, 60);
  }
}

function closeAllModals(){ var r = document.getElementById('modalRoot'); if (r) r.innerHTML = ''; }

function applyTheme(){
  var t = State.theme;
  var prefersDark = false;
  try { prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches; } catch(e){}
  var dark = t === 'dark' || (t === 'system' && prefersDark);
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
}

function setTheme(t){
  State.theme = t;
  safeStorageSet('kf_theme', t);
  applyTheme();
}

try { window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(){ if (State.theme==='system') applyTheme(); }); } catch(e){}

function navigate(hash){ if(location.hash === hash) rerender(); else location.hash = hash; }
function rerender(){ window.dispatchEvent(new Event('hashchange')); }


export { safeStorageGet, safeStorageSet, safeStorageRemove, __kfShowError, hideBoot, State, $, $$, esc, initials, avatar, timeAgo, fmtDate, debounce, verifiedBadge, toast, openModal, closeModal, closeAllModals, applyTheme, setTheme, navigate, rerender };
