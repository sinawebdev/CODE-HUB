// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { $, State, avatar, closeModal, esc, hideBoot, openModal, rerender, setTheme, verifiedBadge } from './core.js';
import { doLogout } from './auth.js';

function svgIcon(name){
  var icons = {
    home:'<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    network:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    briefcase:'<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    building:'<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M9 6h.01M15 6h.01M9 10h.01M15 10h.01M9 14h.01M15 14h.01"/>',
    map:'<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    message:'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    calendar:'<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    bell:'<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    user:'<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    search:'<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    bookmark:'<path d="m19 21-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
    more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    logout:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    plus:'<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>'
  };
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (icons[name]||'') + '</svg>';
}

function buildSidebar(active){
  var items = [
    { key:'home', label:'Home', href:'#/', icon:'home' },
    { key:'network', label:'My Network', href:'#/network', icon:'network', badge: State.counts.connectionRequests },
    { key:'messages', label:'Messages', href:'#/messages', icon:'message', badge: State.counts.messages },
    { key:'notifications', label:'Notifications', href:'#/notifications', icon:'bell', badge: State.counts.notifications },
    { key:'jobs', label:'Jobs', href:'#/jobs', icon:'briefcase' },
    { key:'companies', label:'Companies', href:'#/companies', icon:'building' },
    { key:'local', label:'KoforLink Local', href:'#/local', icon:'map' },
    { key:'events', label:'Events', href:'#/events', icon:'calendar' },
    { key:'profile', label:'Profile', href:'#/profile', icon:'user' },
    { key:'settings', label:'Settings', href:'#/settings', icon:'settings' }
  ];
  if (State.isStaff) items.push({ key:'admin', label:'Admin Center', href:'#/admin', icon:'shield' });
  var name = State.user.FirstName + ' ' + State.user.LastName;
  var html = '<a href="#/" class="brand" aria-label="KoforLink home"><div class="brand-mark">KL</div><div class="brand-name">Kofor<span>Link</span></div></a>' +
    '<div class="workspace-region">Eastern Region, Ghana</div>' +
    '<button class="workspace-search" data-goto="#/search">' + svgIcon('search') + '<span>Search KoforLink</span></button>' +
    '<nav class="workspace-nav" aria-label="Main navigation"><div class="nav-section-label">Your workspace</div>';
  items.forEach(function(i){
    if (i.key === 'jobs') html += '<div class="nav-section-label">Discover</div>';
    if (i.key === 'profile') html += '<div class="nav-section-label">Your account</div>';
    html += '<a class="nav-item ' + (active===i.key?'active':'') + '" href="' + i.href + '"' + (active===i.key?' aria-current="page"':'') + '>' +
      svgIcon(i.icon) + '<span>' + esc(i.label) + '</span>' +
      (i.badge ? '<span class="nav-badge">' + (i.badge>99?'99+':i.badge) + '</span>' : '') +
      '</a>';
  });
  html += '</nav><div class="sidebar-footer">' +
    '<button class="user-chip" data-goto="#/profile">' +
      avatar(State.profilePhoto, name, '40') +
      '<div class="user-chip-info">' +
        '<div class="user-chip-name">' + esc(name) + (State.user.Verified ? ' ' + verifiedBadge() : '') + '</div>' +
        '<div class="user-chip-sub">' + esc(State.user.ProfessionalTitle || State.user.Role) + '</div>' +
      '</div>' +
    '</button>' +
    '<button class="nav-item" id="themeToggleSide" aria-label="Change theme, current theme ' + esc(State.theme) + '">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z"/></svg>' +
      '<span>Theme: ' + esc(State.theme) + '</span>' +
    '</button>' +
    '<button class="nav-item" id="logoutBtn">' + svgIcon('logout') + '<span>Sign out</span></button>' +
  '</div>';
  return html;
}

function buildBottomNav(active){
  var items = [
    { key:'home', label:'Home', href:'#/', icon:'home' },
    { key:'network', label:'Network', href:'#/network', icon:'network', badge: State.counts.connectionRequests },
    { key:'jobs', label:'Jobs', href:'#/jobs', icon:'briefcase' },
    { key:'messages', label:'Messages', href:'#/messages', icon:'message', badge: State.counts.messages }
  ];
  return items.map(function(i){
    return '<button data-goto="' + i.href + '" class="' + (active===i.key?'active':'') + '"' + (active===i.key?' aria-current="page"':'') + '>' +
      svgIcon(i.icon) + '<span>' + esc(i.label) + '</span>' +
      (i.badge ? '<span class="nav-badge">' + (i.badge>9?'9+':i.badge) + '</span>' : '') +
      '</button>';
  }).join('') + '<button id="mobileMore" aria-label="More navigation">' + svgIcon('more') + '<span>More</span></button>';
}

function shell(active, opts){
  opts = opts || {};
  hideBoot();
  $('#landing').classList.add('hidden');
  $('#auth').classList.add('hidden');
  $('#appShell').classList.remove('hidden');
  $('#sidebar').innerHTML = buildSidebar(active);
  $('#bottomNav').innerHTML = buildBottomNav(active);
  $('#shellGrid').className = 'shell' + (opts.noRail ? ' no-rail' : '') + (opts.full ? ' full' : '');
  $('#rail').innerHTML = opts.noRail || opts.full ? '' : buildRail();
  $('#main').className = 'main' + (opts.wide ? ' wide' : '');
  $('#main').setAttribute('data-page', active);
  $('#main').setAttribute('tabindex', '-1');
  $('#bottomNav').setAttribute('aria-label', 'Mobile navigation');
  bindShellEvents();
  if (!opts.noRail && !opts.full) loadRail();
  var dot = $('#mobileNotifDot'); if (dot) dot.classList.toggle('hidden', !State.counts.notifications);
}

function bindShellEvents(){
  var side = $('#themeToggleSide'); if (side) side.onclick = cycleTheme;
  var mb = $('#themeToggleMobile'); if (mb) mb.onclick = cycleTheme;
  var lo = $('#logoutBtn'); if (lo) lo.onclick = doLogout;
  var more = $('#mobileMore'); if (more) more.onclick = openMobileNavigation;
}

function openMobileNavigation(){
  var items = [
    ['Your profile', '#/profile', 'user'],
    ['Companies', '#/companies', 'building'], ['KoforLink Local', '#/local', 'map'],
    ['Events', '#/events', 'calendar'], ['Notifications', '#/notifications', 'bell'],
    ['Settings', '#/settings', 'settings'], ['Search', '#/search', 'search']
  ];
  if (State.isStaff) items.push(['Admin Center', '#/admin', 'shield']);
  var wrap = openModal({ title:'Explore KoforLink', size:'sm', body:
    '<nav class="mobile-more-links" aria-label="More navigation">' + items.map(function(i){
      return '<a class="nav-item" href="' + i[1] + '">' + svgIcon(i[2]) + '<span>' + esc(i[0]) + '</span></a>';
    }).join('') + '</nav>', footer:'<button class="btn btn-secondary" id="mobileSignOut">Sign out</button>' });
  wrap.setAttribute('aria-label', 'Explore KoforLink');
  wrap.querySelectorAll('a').forEach(function(link){ link.onclick = function(){ closeModal(wrap); }; });
  $('#mobileSignOut').onclick = function(){ closeModal(wrap); doLogout(); };
}

function cycleTheme(){
  var order = ['light','dark','system'];
  setTheme(order[(order.indexOf(State.theme)+1)%3]);
  if (State.user) rerender();
}

function buildRail(){
  return '<div class="rail-intro"><div class="section-eyebrow">Close to home</div><h2>Your next step,<br>around the corner.</h2><p>Explore the people and places shaping the Eastern Region.</p></div>' +
    '<section class="rail-card rail-discover" aria-labelledby="railDiscoverTitle">' +
      '<h3 id="railDiscoverTitle">Explore nearby</h3>' +
      '<a class="rail-link" href="#/jobs/near">' + svgIcon('briefcase') + '<span>Jobs near you<small>Find your next opportunity</small></span><span aria-hidden="true">&rarr;</span></a>' +
      '<a class="rail-link" href="#/companies/near">' + svgIcon('building') + '<span>Local companies<small>Get to know local businesses</small></span><span aria-hidden="true">&rarr;</span></a>' +
      '<a class="rail-link" href="#/events">' + svgIcon('calendar') + '<span>Community events<small>Meet, learn and connect</small></span><span aria-hidden="true">&rarr;</span></a>' +
      '<button class="btn btn-primary btn-block btn-sm" data-new-post>' + svgIcon('plus') + ' Share an update</button>' +
    '</section>' +
    '<div class="rail-card" id="railSuggestions">' +
      '<div class="rail-section-head"><h3>Grow your circle</h3><a href="#/network">View all</a></div>' +
      '<div class="skeleton sk-line" style="width:80%"></div>' +
      '<div class="skeleton sk-line" style="width:60%"></div>' +
    '</div>' +
    '<div class="rail-card">' +
      '<div class="rail-section-head"><h3>Skills in the community</h3></div>' +
      '<div id="railTrending"><div class="skeleton sk-line" style="width:70%"></div><div class="skeleton sk-line" style="width:50%"></div></div>' +
    '</div>';
}

function loadRail(){
  Promise.all([
    api.getSuggestions(4).catch(function(){ return { data: [] }; }),
    api.getTrending().catch(function(){ return { data: {} }; })
  ]).then(function(results){
    var sug = results[0], trend = results[1];
    var sEl = $('#railSuggestions');
    if (sEl) {
      var list = (sug && sug.data) || [];
      var html = '<div class="rail-section-head"><h3>Grow your circle</h3><a href="#/network">View all</a></div>';
      if (list.length) {
        list.forEach(function(p){
          html += '<div class="rail-person">' +
            avatar(p.photo, p.name, '40') +
            '<div class="rail-person-info">' +
              '<a href="#/user/' + esc(p.userId) + '" class="rail-person-name ellipsis">' + esc(p.name) + (p.verified ? ' ' + verifiedBadge() : '') + '</a>' +
              '<div class="ellipsis small muted">' + esc(p.headline||p.city||'') + '</div>' +
            '</div>' +
            '<button class="rail-connect" data-connect="' + esc(p.userId) + '" aria-label="Connect with ' + esc(p.name) + '" title="Connect">' + svgIcon('plus') + '</button>' +
          '</div>';
        });
      } else { html += '<p class="rail-empty">Your network starts with a hello.</p><a class="rail-text-link" href="#/network">Find people to connect with &rarr;</a>'; }
      sEl.innerHTML = html;
    }
    var tEl = $('#railTrending');
    if (tEl) {
      var skills = trend && trend.data && trend.data.skills || [];
      tEl.innerHTML = skills.length ? skills.map(function(s){
        return '<span class="rail-skill">' + esc(s.name) + ' <span class="muted">' + s.count + '</span></span>';
      }).join('') : '<p class="rail-empty">Skills shared by your community will appear here.</p>';
    }
  }).catch(function(){});
}

function refreshCounts(){
  api.bootstrap().then(function(res){
    State.counts = res.data.counts || State.counts;
    var side = $('#sidebar'); if (side && State.user) side.innerHTML = buildSidebar(currentActiveKey());
    var bn = $('#bottomNav'); if (bn && State.user) bn.innerHTML = buildBottomNav(currentActiveKey());
    bindShellEvents();
    var dot = $('#mobileNotifDot'); if (dot) dot.classList.toggle('hidden', !State.counts.notifications);
  }).catch(function(){});
}

function currentActiveKey(){
  var h = location.hash || '#/';
  if (h.indexOf('#/network')===0) return 'network';
  if (h.indexOf('#/jobs')===0) return 'jobs';
  if (h.indexOf('#/companies')===0) return 'companies';
  if (h.indexOf('#/local')===0) return 'local';
  if (h.indexOf('#/messages')===0) return 'messages';
  if (h.indexOf('#/events')===0) return 'events';
  if (h.indexOf('#/notifications')===0) return 'notifications';
  if (h.indexOf('#/profile')===0 || h.indexOf('#/user')===0) return 'profile';
  if (h.indexOf('#/settings')===0) return 'settings';
  if (h.indexOf('#/admin')===0) return 'admin';
  return 'home';
}

export { svgIcon, buildSidebar, buildBottomNav, shell, bindShellEvents, cycleTheme, buildRail, loadRail, refreshCounts, currentActiveKey };
