// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { refreshCounts, shell, svgIcon } from './layout.js';
import { $, avatar, esc, timeAgo, toast } from './core.js';

function renderNotifications(){
  shell('notifications', { wide:true, noRail:true });
  $('#main').innerHTML =
    '<div class="flex-between mb-4"><h1>Notifications</h1><button class="btn btn-secondary btn-sm" id="markAllBtn">Mark all read</button></div>' +
    '<div id="notifList"><div class="center-loader"><span class="spinner dark"></span></div></div>';
  $('#markAllBtn').onclick = function(){
    api.markAllNotificationsRead().then(function(){ toast('All marked read'); renderNotifications(); refreshCounts(); })
      .catch(function(e){ toast(e.message||'Failed', 'error'); });
  };
  api.getNotifications(50).then(function(res){
    var list = res.data.notifications || [];
    var el = $('#notifList');
    if (list.length) {
      el.innerHTML = '<div class="card" style="overflow:hidden">' + list.map(function(n){
        return '<div class="notif ' + (n.read?'':'unread') + '" data-notif-link="' + esc(n.link) + '" data-notif-id="' + esc(n.id) + '">' +
          (n.actorPhoto ? avatar(n.actorPhoto, '', '40') : '<div class="notif-icon">' + svgIcon('bell') + '</div>') +
          '<div class="notif-body"><div class="notif-title">' + esc(n.title) + '</div><div class="notif-text">' + esc(n.body) + '</div>' +
          '<div class="small muted mt-2">' + esc(n.timeAgo) + '</div></div></div>';
      }).join('') + '</div>';
    } else {
      el.innerHTML = '<div class="empty"><div class="empty-icon">' + svgIcon('bell') + '</div><h3>No notifications</h3><p>You are all caught up.</p></div>';
    }
    el.querySelectorAll('[data-notif-link]').forEach(function(x){ x.onclick = function(){
      var id = x.getAttribute('data-notif-id'), link = x.getAttribute('data-notif-link');
      api.markNotificationRead(id).catch(function(){});
      if (link) location.hash = link;
      refreshCounts();
    }; });
  }).catch(function(e){ $('#notifList').innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

export { renderNotifications };
