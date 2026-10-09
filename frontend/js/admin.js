// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { $, $$, State, avatar, closeAllModals, esc, openModal, timeAgo, toast } from './core.js';
import { shell, svgIcon } from './layout.js';

function renderAdmin(){
  if (!State.isStaff) { location.hash = '#/'; return; }
  shell('admin', { wide:true, noRail:true });
  $('#main').innerHTML =
    '<h1 class="mb-4">Admin Center</h1>' +
    '<div class="grid grid-4 mb-4" id="adminStats">' +
      Array(8).fill(0).map(function(){ return '<div class="stat-card"><div class="skeleton sk-line" style="width:60%"></div><div class="skeleton" style="height:26px;width:40%;margin-top:8px"></div></div>'; }).join('') +
    '</div>' +
    '<div class="tabs">' +
      '<button class="tab active" data-admin-tab="overview">Overview</button>' +
      '<button class="tab" data-admin-tab="users">Users</button>' +
      '<button class="tab" data-admin-tab="companies">Companies</button>' +
      '<button class="tab" data-admin-tab="jobs">Jobs</button>' +
      '<button class="tab" data-admin-tab="posts">Posts</button>' +
      '<button class="tab" data-admin-tab="reports">Reports</button>' +
      '<button class="tab" data-admin-tab="verification">Verification</button>' +
      '<button class="tab" data-admin-tab="settings">Platform Settings</button>' +
    '</div>' +
    '<div id="adminContent"><div class="center-loader"><span class="spinner dark"></span></div></div>';
  api.adminStats().then(function(res){
    var s = res.data;
    $('#adminStats').innerHTML = [
      { label:'Total users', value:s.totalUsers, icon:'user' },
      { label:'Unverified emails', value:s.unverifiedEmails, icon:'bell' },
      { label:'Companies', value:s.companies, icon:'building' },
      { label:'Open jobs', value:s.jobs, icon:'briefcase' },
      { label:'Applications', value:s.applications, icon:'briefcase' },
      { label:'Active posts', value:s.posts, icon:'home' },
      { label:'Pending reports', value:s.reports, icon:'shield' },
      { label:'Pending verifications', value:s.pendingVerifications, icon:'shield' }
    ].map(function(x){
      return '<div class="stat-card"><div class="stat-label">' + esc(x.label) + '</div>' +
        '<div class="stat-value">' + x.value + '</div>' +
        '<div class="stat-icon">' + svgIcon(x.icon) + '</div></div>';
    }).join('');

    var tabs = {
      overview: function(){
        return '<div class="card card-pad mb-4"><h3 class="mb-3">New signups (last 7 days)</h3>' +
            '<div class="bar-chart">' + s.signupTrend.map(function(d){
              var max = Math.max.apply(null, s.signupTrend.map(function(x){ return x.value; }).concat([1]));
              return '<div class="bar-col"><div class="bar-value">' + d.value + '</div><div class="bar" style="height:' + Math.max(4, (d.value/max)*100) + '%"></div><div class="bar-label">' + esc(d.label) + '</div></div>';
            }).join('') + '</div></div>' +
          '<div class="card card-pad mb-4"><h3 class="mb-3">Posts created (last 7 days)</h3>' +
            '<div class="bar-chart">' + s.postTrend.map(function(d){
              var max = Math.max.apply(null, s.postTrend.map(function(x){ return x.value; }).concat([1]));
              return '<div class="bar-col"><div class="bar-value">' + d.value + '</div><div class="bar" style="height:' + Math.max(4, (d.value/max)*100) + '%"></div><div class="bar-label">' + esc(d.label) + '</div></div>';
            }).join('') + '</div></div>' +
          '<div class="card card-pad"><h3 class="mb-3">Role breakdown</h3>' + s.roleBreakdown.map(function(r){
              return '<div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--border)"><div class="bold">' + esc(r.label) + '</div><div>' + r.value + '</div></div>';
            }).join('') + '</div>';
      },
      users: function(){ return '<div id="adminListBody"><div class="center-loader"><span class="spinner dark"></span></div></div>'; },
      companies: function(){ return '<div id="adminListBody"><div class="center-loader"><span class="spinner dark"></span></div></div>'; },
      jobs: function(){ return '<div id="adminListBody"><div class="center-loader"><span class="spinner dark"></span></div></div>'; },
      posts: function(){ return '<div id="adminListBody"><div class="center-loader"><span class="spinner dark"></span></div></div>'; },
      reports: function(){ return '<div id="adminListBody"><div class="center-loader"><span class="spinner dark"></span></div></div>'; },
      verification: function(){ return '<div id="adminListBody"><div class="center-loader"><span class="spinner dark"></span></div></div>'; },
      settings: function(){ return '<div id="adminSettingsBody"><div class="center-loader"><span class="spinner dark"></span></div></div>'; }
    };
    var renderTab = function(t){
      $('#adminContent').innerHTML = tabs[t] ? tabs[t]() : '';
      if (t === 'verification') loadAdminVerifications();
      else if (['users','companies','jobs','posts','reports'].indexOf(t) !== -1) loadAdminList(t);
      else if (t === 'settings') loadAdminSettings();
    };
    $$('[data-admin-tab]').forEach(function(t){ t.onclick = function(){
      $$('[data-admin-tab]').forEach(function(x){ x.classList.remove('active'); });
      t.classList.add('active'); renderTab(t.getAttribute('data-admin-tab'));
    }; });
    renderTab('overview');
  }).catch(function(e){ toast(e.message||'Failed', 'error'); });
}

function loadAdminList(resource){
  var el = $('#adminListBody'); if (!el) return;
  api.adminList(resource, {}).then(function(res){
    var list = res.data || [];
    if (!list.length) { el.innerHTML = '<div class="card"><div class="empty" style="padding:40px"><p>No ' + esc(resource) + ' found.</p></div></div>'; return; }
    var keys = Object.keys(list[0]).slice(0, 6);
    var html = '<div class="card" style="overflow-x:auto"><table class="tbl"><thead><tr>';
    keys.forEach(function(k){ html += '<th>' + esc(k) + '</th>'; });
    html += '<th></th></tr></thead><tbody>';
    list.forEach(function(row){
      html += '<tr>';
      keys.forEach(function(k){ html += '<td>' + esc(String(row[k]===null?'':row[k]).substring(0,60)) + '</td>'; });
      html += '<td>' + (row.UserID && resource==='users' ? '<button class="btn btn-xs btn-secondary" data-admin-user="' + esc(row.UserID) + '">Manage</button>' : '') + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table></div>';
    el.innerHTML = html;
    el.querySelectorAll('[data-admin-user]').forEach(function(b){ b.onclick = function(){ var row=list.find(function(item){return item.UserID===b.getAttribute('data-admin-user');});openAdminUserMenu(row.UserID,row.Role,row.Status,row.FullName || ((row.FirstName||'')+' '+(row.LastName||'')));  }; });
  }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

function loadAdminVerifications(){
  var el = $('#adminListBody'); if (!el) return;
  el.innerHTML = '<div class="card card-pad mb-3" style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">' +
      '<div class="flex gap-2" style="flex-wrap:wrap">' +
        ['All','Pending','Approved','Rejected','Suspended'].map(function(s, i){
          return '<button class="chip ' + (s==='Pending'?'active':'') + '" data-ver-filter="' + s + '">' + s + '</button>';
        }).join('') +
      '</div>' +
    '</div>' +
    '<div id="verList"></div>';
  var currentFilter = 'Pending';
  var load = function(){
    var listEl = $('#verList');
    listEl.innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
    api.adminGetVerifications(currentFilter).then(function(res){
      var rows = res.data || [];
      if (!rows.length) { listEl.innerHTML = '<div class="card"><div class="empty" style="padding:40px"><p>No ' + esc(currentFilter.toLowerCase()) + ' verification requests.</p></div></div>'; return; }
      listEl.innerHTML = rows.map(function(v){
        var statusBadge = v.status === 'Approved' ? 'badge-success' :
                          v.status === 'Rejected' ? 'badge-danger' :
                          v.status === 'Suspended' ? 'badge-gray' : 'badge-accent';
        return '<div class="card card-pad mb-3">' +
          '<div class="flex gap-3" style="align-items:flex-start">' +
            avatar(v.userPhoto, v.userName, '48') +
            '<div style="flex:1;min-width:0">' +
              '<div class="flex-between" style="flex-wrap:wrap;gap:10px">' +
                '<div>' +
                  '<div style="font-weight:600">' + esc(v.userName) + ' <span class="small muted">(' + esc(v.userRole) + ')</span></div>' +
                  '<div class="small muted">' + esc(v.userEmail) + '</div>' +
                '</div>' +
                '<span class="badge ' + statusBadge + '">' + esc(v.status) + '</span>' +
              '</div>' +
              '<div class="small muted mt-2">' +
                'Type: <b>' + esc(v.type) + '</b>' +
                (v.companyName ? ' · Company: <b>' + esc(v.companyName) + '</b>' : '') +
                ' · Submitted ' + esc(v.timeAgo) +
              '</div>' +
              (v.notes ? '<div class="mt-2 small" style="background:var(--surface-3);padding:10px 12px;border-radius:10px"><b>Notes:</b> ' + esc(v.notes) + '</div>' : '') +
              (v.rejectionReason ? '<div class="mt-2 small" style="background:var(--danger-50);color:var(--danger);padding:10px 12px;border-radius:10px"><b>Rejection reason:</b> ' + esc(v.rejectionReason) + '</div>' : '') +
            '</div>' +
          '</div>' +
          (v.status === 'Pending'
            ? '<div class="flex gap-2 mt-3" style="flex-wrap:wrap">' +
                '<button class="btn btn-primary btn-sm" data-ver-approve="' + esc(v.id) + '">Approve</button>' +
                '<button class="btn btn-danger btn-sm" data-ver-reject="' + esc(v.id) + '">Reject</button>' +
                '<button class="btn btn-secondary btn-sm" data-ver-suspend="' + esc(v.id) + '">Suspend</button>' +
              '</div>'
            : '') +
        '</div>';
      }).join('');
      $$('[data-ver-approve]', listEl).forEach(function(b){ b.onclick = function(){ reviewVerification(b.getAttribute('data-ver-approve'), 'approve'); }; });
      $$('[data-ver-reject]', listEl).forEach(function(b){ b.onclick = function(){ reviewVerification(b.getAttribute('data-ver-reject'), 'reject'); }; });
      $$('[data-ver-suspend]', listEl).forEach(function(b){ b.onclick = function(){ reviewVerification(b.getAttribute('data-ver-suspend'), 'suspend'); }; });
    }).catch(function(e){ listEl.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
  };
  $$('[data-ver-filter]', el).forEach(function(b){ b.onclick = function(){
    $$('[data-ver-filter]', el).forEach(function(x){ x.classList.remove('active'); });
    b.classList.add('active');
    currentFilter = b.getAttribute('data-ver-filter');
    load();
  }; });
  load();
}

function reviewVerification(id, decision){
  if (decision === 'reject') {
    openModal({
      title:'Reject verification', size:'sm',
      body:'<div class="field"><label>Reason for rejection *</label>' +
        '<textarea class="textarea" id="rejReason" rows="4" placeholder="Explain why this request was not approved..."></textarea>' +
        '<div class="field-hint">This will be shared with the applicant.</div></div>',
      footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
        '<button class="btn btn-danger" id="rejConfirm">Reject request</button>'
    });
    $('#rejConfirm').onclick = function(){
      var reason = $('#rejReason').value.trim();
      if (!reason) { toast('Please provide a reason', 'error'); return; }
      var b = this; b.disabled = true; b.innerHTML = '<span class="spinner"></span>';
      api.adminReviewVerification(id, 'reject', reason).then(function(){
        closeAllModals(); toast('Verification rejected'); loadAdminVerifications();
      }).catch(function(e){ toast(e.message||'Failed', 'error'); b.disabled = false; b.textContent = 'Reject request'; });
    };
    return;
  }
  var label = decision === 'approve' ? 'Approve' : 'Suspend';
  if (!confirm(label + ' this verification request?')) return;
  api.adminReviewVerification(id, decision, '').then(function(){
    toast('Verification ' + (decision === 'approve' ? 'approved' : 'suspended'));
    loadAdminVerifications();
  }).catch(function(e){ toast(e.message||'Failed', 'error'); });
}

function openAdminUserMenu(userId, currentRole, currentStatus, name){
  openModal({
    title:'Manage user', size:'sm',
    body:'<p class="mb-3">' + esc(name||userId) + '</p><div class="field"><label>Role</label>' +
        '<select class="select" id="auRole">' + ['Super Admin','Admin','Moderator','Employer','Professional','Student','Normal User'].map(function(r){ return '<option ' + (r===currentRole?'selected':'') + '>' + r + '</option>';  }).join('') + '</select></div>' +
      '<div class="field"><label>Status</label>' +
        '<select class="select" id="auStatus">' + ['Active','Suspended','Disabled','Pending'].map(function(s){ return '<option ' + (s===currentStatus?'selected':'') + '>' + s + '</option>';  }).join('') + '</select></div>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="auSave">Save</button>'
  });
  $('#auSave').onclick = function(){
    var role=$('#auRole').value, status=$('#auStatus').value, btn=this;btn.disabled=true;
    Promise.resolve().then(function(){if(role!==currentRole)return api.adminSetUserRole(userId,role);})
      .then(function(){if(status!==currentStatus)return api.adminSetUserStatus(userId,status);})
      .then(function(){closeAllModals();toast('Updated');loadAdminList('users');})
      .catch(function(e){ toast(e.message||'Failed', 'error'); btn.disabled=false; });
  };
}

function loadAdminSettings(){
  var el = $('#adminSettingsBody'); if (!el) return;
  api.adminGetSettings().then(function(res){
    var s = res.data;
    el.innerHTML = '<div class="card card-pad">' +
      '<h3 class="mb-3">Platform settings</h3>' +
      '<div class="field"><label>Platform name</label><input class="input" id="asName" value="' + esc(s.platformName||'') + '"></div>' +
      '<div class="row"><div class="field"><label>Primary color</label><input class="input" type="color" id="asPrimary" value="' + esc(s.primaryColor||'#0E7C4A') + '"></div>' +
        '<div class="field"><label>Secondary color</label><input class="input" type="color" id="asSecondary" value="' + esc(s.secondaryColor||'#F2B705') + '"></div></div>' +
      '<div class="row"><div class="field"><label>Default city</label><input class="input" id="asCity" value="' + esc(s.defaultCity||'') + '"></div>' +
        '<div class="field"><label>Default region</label><input class="input" id="asRegion" value="' + esc(s.defaultRegion||'') + '"></div></div>' +
      '<div class="field"><label class="flex gap-2" style="cursor:pointer"><input type="checkbox" id="asReg" ' + (s.registrationEnabled==='TRUE'?'checked':'') + '> Allow registration</label></div>' +
      '<div class="field"><label class="flex gap-2" style="cursor:pointer"><input type="checkbox" id="asEmp" ' + (s.employerRegistration==='TRUE'?'checked':'') + '> Allow employer registration</label></div>' +
      '<div class="field"><label class="flex gap-2" style="cursor:pointer"><input type="checkbox" id="asEmail" ' + (s.emailNotifications==='TRUE'?'checked':'') + '> Send email notifications</label></div>' +
      '<div class="field"><label class="flex gap-2" style="cursor:pointer"><input type="checkbox" id="asMaint" ' + (s.maintenanceMode==='TRUE'?'checked':'') + '> Maintenance mode</label></div>' +
      '<button class="btn btn-primary" id="asSave">Save settings</button>' +
    '</div>';
    $('#asSave').onclick = function(){
      api.adminSaveSettings({
        platformName: $('#asName').value.trim(),
        primaryColor: $('#asPrimary').value,
        secondaryColor: $('#asSecondary').value,
        defaultCity: $('#asCity').value.trim(),
        defaultRegion: $('#asRegion').value.trim(),
        registrationEnabled: $('#asReg').checked ? 'TRUE' : 'FALSE',
        employerRegistration: $('#asEmp').checked ? 'TRUE' : 'FALSE',
        emailNotifications: $('#asEmail').checked ? 'TRUE' : 'FALSE',
        maintenanceMode: $('#asMaint').checked ? 'TRUE' : 'FALSE'
      }).then(function(){ toast('Settings saved'); }).catch(function(e){ toast(e.message||'Failed', 'error'); });
    };
  }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

export { renderAdmin, loadAdminList, loadAdminVerifications, reviewVerification, openAdminUserMenu, loadAdminSettings };
