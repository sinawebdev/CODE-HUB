// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { refreshCounts, shell, svgIcon } from './layout.js';
import { $, $$, avatar, esc, toast, verifiedBadge } from './core.js';

function renderNetwork(){
  shell('network', { wide:true });
  $('#main').innerHTML =
    '<header class="page-introduction"><h1>My network</h1><p>Meet people, build connections and stay in touch.</p></header>' +
    '<div class="tabs">' +
      '<button class="tab active" data-net-tab="requests">Invitations</button>' +
      '<button class="tab" data-net-tab="connections">Connections</button>' +
      '<button class="tab" data-net-tab="suggestions">Suggestions</button>' +
      '<button class="tab" data-net-tab="following">Following</button>' +
    '</div>' +
    '<div id="netContent"><div class="center-loader"><span class="spinner dark"></span></div></div>';
  $$('[data-net-tab]').forEach(function(t){ t.onclick = function(){
    $$('[data-net-tab]').forEach(function(x){ x.classList.remove('active'); });
    t.classList.add('active');
    loadNetworkTab(t.getAttribute('data-net-tab'));
  }; });
  loadNetworkTab('requests');
}

function loadNetworkTab(tab){
  var el = $('#netContent'); if (!el) return;
  el.innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  if (tab === 'requests') {
    api.getConnectionRequests().then(function(res){
      var incoming = res.data.incoming, outgoing = res.data.outgoing;
      var html = '';
      if (incoming.length) html += '<h3 class="mb-3">Pending invitations (' + incoming.length + ')</h3><div class="grid grid-3">' + incoming.map(function(p){ return personCard(p, 'incoming'); }).join('') + '</div>';
      if (outgoing.length) html += '<h3 class="mb-3 mt-4">Sent requests (' + outgoing.length + ')</h3><div class="grid grid-3">' + outgoing.map(function(p){ return personCard(p, 'outgoing'); }).join('') + '</div>';
      if (!incoming.length && !outgoing.length) html += '<div class="empty"><div class="empty-icon">' + svgIcon('network') + '</div><h3>No pending invitations</h3><p>When someone sends you a connection request it will appear here.</p></div>';
      el.innerHTML = html;
    }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed to load') + '</p></div>'; });
  } else if (tab === 'connections') {
    api.getConnections('').then(function(res){
      var list = res.data || [];
      el.innerHTML = list.length ? '<div class="grid grid-3">' + list.map(function(p){ return personCard(p, 'connected'); }).join('') + '</div>'
        : '<div class="empty"><div class="empty-icon">' + svgIcon('network') + '</div><h3>No connections yet</h3><p>Start building your network by connecting with professionals.</p></div>';
    }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
  } else if (tab === 'suggestions') {
    api.getSuggestions(30).then(function(res){
      var list = res.data || [];
      el.innerHTML = list.length ? '<div class="grid grid-3">' + list.map(function(p){ return personCard(p, 'suggested'); }).join('') + '</div>'
        : '<div class="empty"><div class="empty-icon">' + svgIcon('network') + '</div><h3>No suggestions right now</h3></div>';
    }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
  } else if (tab === 'following') {
    api.getFollowers('', 'following').then(function(res){
      var list = res.data || [];
      el.innerHTML = list.length ? '<div class="grid grid-3">' + list.map(function(p){ return personCard(p, 'following'); }).join('') + '</div>'
        : '<div class="empty"><div class="empty-icon">' + svgIcon('network') + '</div><h3>You are not following anyone yet</h3></div>';
    }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
  }
}

function personCard(p, mode){
  var html = '<div class="card card-pad" style="text-align:center">' +
    '<div style="display:flex;justify-content:center">' +
      '<a href="#/user/' + esc(p.userId) + '">' + avatar(p.photo, p.name, '72') + '</a>' +
    '</div>' +
    '<div style="font-weight:600;margin-top:10px;font-size:14px">' +
      '<a href="#/user/' + esc(p.userId) + '" style="color:inherit">' + esc(p.name) + '</a>' +
      (p.verified ? ' ' + verifiedBadge() : '') +
    '</div>' +
    '<div class="small muted" style="margin-top:4px;min-height:32px">' + esc(p.headline||p.city||'') + '</div>' +
    (p.mutual ? '<div class="small muted" style="margin-top:4px">' + p.mutual + ' mutual connection' + (p.mutual>1?'s':'') + '</div>' : '') +
    '<div class="flex gap-2 mt-3" style="justify-content:center;flex-wrap:wrap">';
  if (mode === 'incoming') html += '<button class="btn btn-primary btn-sm" data-accept="' + esc(p.connectionId) + '">Accept</button>' +
      '<button class="btn btn-secondary btn-sm" data-reject="' + esc(p.connectionId) + '">Ignore</button>';
  else if (mode === 'outgoing') html += '<button class="btn btn-secondary btn-sm" data-withdraw="' + esc(p.connectionId) + '">Withdraw</button>';
  else if (mode === 'suggested') html += '<button class="btn btn-outline btn-sm" data-connect="' + esc(p.userId) + '">Connect</button>';
  else if (mode === 'connected') html += '<button class="btn btn-secondary btn-sm" data-goto="#/messages/' + esc(p.userId) + '">Message</button>';
  else if (mode === 'following') html += '<button class="btn btn-secondary btn-sm" data-unfollow="' + esc(p.userId) + '">Unfollow</button>';
  html += '</div></div>';
  return html;
}

document.addEventListener('click', function(e){
  var acc = e.target.closest('[data-accept]');
  if (acc) { api.respondConnection(acc.getAttribute('data-accept'), 'accept').then(function(){ toast('Connection accepted'); refreshCounts(); loadNetworkTab('requests'); }).catch(function(err){ toast(err.message||'Failed','error'); }); return; }
  var rej = e.target.closest('[data-reject]');
  if (rej) { api.respondConnection(rej.getAttribute('data-reject'), 'reject').then(function(){ toast('Request ignored'); refreshCounts(); loadNetworkTab('requests'); }).catch(function(err){ toast(err.message||'Failed','error'); }); return; }
  var wd = e.target.closest('[data-withdraw]');
  if (wd) { api.respondConnection(wd.getAttribute('data-withdraw'), 'cancel').then(function(){ toast('Request withdrawn'); refreshCounts(); loadNetworkTab('requests'); }).catch(function(err){ toast(err.message||'Failed','error'); }); return; }
  var uf = e.target.closest('[data-unfollow]');
  if (uf) { api.follow(uf.getAttribute('data-unfollow'), false).then(function(){ toast('Unfollowed'); loadNetworkTab('following'); }).catch(function(err){ toast(err.message||'Failed','error'); }); }
});

function doConnect(userId){
  api.sendConnection(userId, '').then(function(){
    toast('Connection request sent');
    if (location.hash.indexOf('#/network')===0) loadNetworkTab('suggestions');
  }).catch(function(e){ toast(e.message||'Failed', 'error'); });
}

export { renderNetwork, loadNetworkTab, personCard, doConnect };
