// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { refreshCounts, shell } from './layout.js';
import { $, $$, avatar, closeAllModals, confirmAction, esc, openModal, toast, verifiedBadge } from './core.js';
import { openConversation } from './messages.js';
import { bindCarousels, openReportModal, postCard } from './feed.js';
import { bootstrap } from './auth.js';

function renderMyProfile(){
  shell('profile', { wide:true, noRail:true });
  $('#main').innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  api.getMyProfile().then(function(res){ renderProfileView(res.data, true); })
    .catch(function(e){ $('#main').innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

function renderUserProfile(userId){
  shell('profile', { wide:true, noRail:true });
  $('#main').innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  api.getProfile(userId).then(function(res){
    if (res.data.restricted) {
      $('#main').innerHTML =
        '<div class="card card-pad" style="text-align:center">' +
          avatar('', res.data.user.FullName, '96') +
          '<h2 class="mt-3">' + esc(res.data.user.FullName) + '</h2>' +
          '<p class="muted mt-2">' + esc(res.data.message) + '</p>' +
        '</div>';
      return;
    }
    renderProfileView(res.data, false);
  }).catch(function(e){ $('#main').innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

function renderProfileView(d, isMe){
  var user = d.user, profile = d.profile, skills = d.skills, experience = d.experience,
      education = d.education, certifications = d.certifications, stats = d.stats;
  var relationship = d.relationship || {};
  var completion = profile.CompletionPct || 0;
  var rel = relationship;

  var connLabel = 'Connect', connClass = 'btn-primary';
  if (rel.connected) { connLabel = 'Connected'; connClass = 'btn-secondary'; }
  else if (rel.pendingOutgoing) { connLabel = 'Pending'; connClass = 'btn-secondary'; }
  else if (rel.pendingIncoming) { connLabel = 'Accept request'; connClass = 'btn-primary'; }

  var html = '<div class="card" style="overflow:hidden">' +
    '<div class="profile-cover">' +
      (profile.CoverPhotoUrl ? '<img src="' + esc(profile.CoverPhotoUrl) + '" alt="">' : '') +
      '<div class="profile-cover-overlay"></div>' +
    '</div>' +
    '<div class="profile-head">' +
      '<div class="flex-between" style="align-items:flex-end;flex-wrap:wrap;gap:12px">' +
        '<div class="profile-avatar-wrap">' + avatar(profile.ProfilePhotoUrl, user.FullName, '96') + '</div>' +
        '<div class="flex gap-2" style="flex-wrap:wrap">';
  if (isMe) {
    html += '<button class="btn btn-primary btn-sm" id="editProfileBtn">Edit profile</button>' +
      '<button class="btn btn-secondary btn-sm" data-goto="#/settings">Settings</button>';
  } else {
    html += '<button class="btn ' + connClass + ' btn-sm" id="connBtn" data-state="' +
        (rel.connected ? 'connected' : rel.pendingOutgoing ? 'outgoing' : rel.pendingIncoming ? 'incoming' : 'none') + '">' + connLabel + '</button>' +
      '<button class="btn btn-secondary btn-sm" id="followBtn">' + (rel.following?'Following':'Follow') + '</button>' +
      '<button class="btn btn-secondary btn-sm" id="messageBtn">Message</button>' +
      '<button class="icon-btn" id="moreProfileBtn"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg></button>';
  }
  html += '</div></div>' +
      '<h1 class="mt-3">' + esc(user.FullName) + (user.Verified ? ' ' + verifiedBadge() : '') + '</h1>' +
      '<p class="muted mt-2" style="font-size:15px">' + esc(profile.Headline||'') + '</p>' +
      '<div class="flex gap-3 small muted mt-2" style="flex-wrap:wrap">' +
        (profile.City ? '<span>' + esc(profile.City) + ', ' + esc(profile.Region) + '</span>' : '') +
        (profile.Website ? '<span><a href="' + esc(profile.Website) + '" target="_blank" rel="noopener noreferrer" style="color:var(--brand)">' + esc(profile.Website) + '</a></span>' : '') +
      '</div>' +
      (isMe ? '<div class="mt-3"><div class="flex-between small"><span class="bold">Profile strength</span><span class="muted">' + completion + '%</span></div>' +
        '<div class="strength"><div class="strength-fill" style="width:' + completion + '%"></div></div></div>' : '') +
      '<div class="flex gap-4 mt-4 small">' +
        '<div><div class="bold">' + stats.connections + '</div><div class="muted">Connections</div></div>' +
        '<div><div class="bold">' + stats.followers + '</div><div class="muted">Followers</div></div>' +
        '<div><div class="bold">' + stats.posts + '</div><div class="muted">Posts</div></div>' +
      '</div>' +
    '</div>' +
  '</div>' +
  '<div class="tabs mt-4">' +
    '<button class="tab active" data-prof-tab="about">About</button>' +
    '<button class="tab" data-prof-tab="experience">Experience</button>' +
    '<button class="tab" data-prof-tab="education">Education</button>' +
    (certifications.length ? '<button class="tab" data-prof-tab="certs">Certifications</button>' : '') +
    '<button class="tab" data-prof-tab="posts">Posts</button>' +
  '</div>' +
  '<div id="profContent"></div>';
  $('#main').innerHTML = html;

  var tabs = {
    about: function(){
      var h = '<div class="card card-pad"><h3 class="mb-3">About</h3>' +
        '<p style="white-space:pre-wrap;line-height:1.7">' + esc(profile.About||'No description yet.') + '</p>';
      if (skills.length) {
        h += '<div class="divider"></div><h3 class="mb-3">Skills</h3><div class="flex gap-2" style="flex-wrap:wrap">' +
          skills.map(function(s){ return '<span class="chip">' + esc(s.name) + '</span>'; }).join('') + '</div>';
      }
      if (profile.Languages||profile.Achievements||profile.Interests) {
        h += '<div class="divider"></div><div class="grid grid-2">' +
          (profile.Languages ? '<div><div class="small muted">Languages</div><div class="bold">' + esc(profile.Languages) + '</div></div>' : '') +
          (profile.Interests ? '<div><div class="small muted">Interests</div><div class="bold">' + esc(profile.Interests) + '</div></div>' : '') +
          (profile.Achievements ? '<div style="grid-column:1/-1"><div class="small muted">Achievements</div><div>' + esc(profile.Achievements) + '</div></div>' : '') +
        '</div>';
      }
      h += '</div>';
      return h;
    },
    experience: function(){
      if (!experience.length) return '<div class="empty"><p>No experience listed.</p>' + (isMe ? '<button class="btn btn-outline btn-sm mt-3" id="addExpBtn">+ Add experience</button>' : '') + '</div>';
      var h = experience.map(function(e){
        return '<div class="card card-pad mb-3"><div class="flex gap-3">' +
          '<div class="job-logo" style="width:44px;height:44px">' + esc((e.company||'C').charAt(0)) + '</div>' +
          '<div style="flex:1"><div style="font-weight:600">' + esc(e.title) + '</div>' +
          '<div class="small">' + esc(e.company) + '</div>' +
          '<div class="small muted">' + esc(e.start||'') + ' - ' + (e.current ? 'Present' : esc(e.end||'')) + (e.location ? ' | ' + esc(e.location) : '') + '</div>' +
          (e.description ? '<p class="small mt-2">' + esc(e.description) + '</p>' : '') + '</div>' +
          (isMe ? '<button class="icon-btn" data-del-exp="' + esc(e.id) + '" style="width:32px;height:32px">×</button>' : '') +
        '</div></div>';
      }).join('');
      if (isMe) h += '<button class="btn btn-outline btn-sm" id="addExpBtn">+ Add experience</button>';
      return h;
    },
    education: function(){
      if (!education.length) return '<div class="empty"><p>No education listed.</p>' + (isMe ? '<button class="btn btn-outline btn-sm mt-3" id="addEduBtn">+ Add education</button>' : '') + '</div>';
      var h = education.map(function(e){
        return '<div class="card card-pad mb-3"><div class="flex gap-3">' +
          '<div class="job-logo" style="width:44px;height:44px">' + esc((e.school||'S').charAt(0)) + '</div>' +
          '<div style="flex:1"><div style="font-weight:600">' + esc(e.school) + '</div>' +
          '<div class="small">' + esc(e.degree||'') + (e.field ? ' | ' + esc(e.field) : '') + '</div>' +
          '<div class="small muted">' + esc(e.startYear||'') + ' - ' + esc(e.endYear||'') + '</div></div>' +
          (isMe ? '<button class="icon-btn" data-del-edu="' + esc(e.id) + '" style="width:32px;height:32px">×</button>' : '') +
        '</div></div>';
      }).join('');
      if (isMe) h += '<button class="btn btn-outline btn-sm" id="addEduBtn">+ Add education</button>';
      return h;
    },
    certs: function(){
      return certifications.map(function(c){
        return '<div class="card card-pad mb-3"><div class="flex-between">' +
          '<div><div style="font-weight:600">' + esc(c.name) + '</div>' +
          '<div class="small muted">' + esc(c.issuer||'') + (c.issueDate ? ' | ' + esc(c.issueDate) : '') + '</div></div>' +
          (isMe ? '<button class="icon-btn" data-del-cert="' + esc(c.id) + '" style="width:32px;height:32px">×</button>' : '') +
        '</div></div>';
      }).join('');
    },
    posts: function(){ return '<div id="profilePosts"><div class="center-loader"><span class="spinner dark"></span></div></div>'; }
  };

  var renderTab = function(t){
    $('#profContent').innerHTML = tabs[t] ? tabs[t]() : '';
    if (isMe) {
      $$('[data-del-exp]').forEach(function(b){ b.onclick = async function(){ if(!await confirmAction({title:'Remove this experience?',message:'This entry will be removed from your profile.'}))return; api.deleteExperience(b.getAttribute('data-del-exp')).then(renderMyProfile).catch(function(e){ toast(e.message||'Failed','error'); }); }; });
      $$('[data-del-edu]').forEach(function(b){ b.onclick = async function(){ if(!await confirmAction({title:'Remove this education?',message:'This entry will be removed from your profile.'}))return; api.deleteEducation(b.getAttribute('data-del-edu')).then(renderMyProfile).catch(function(e){ toast(e.message||'Failed','error'); }); }; });
      $$('[data-del-cert]').forEach(function(b){ b.onclick = async function(){ if(!await confirmAction({title:'Remove this certification?',message:'This entry will be removed from your profile.'}))return; api.deleteCertification(b.getAttribute('data-del-cert')).then(renderMyProfile).catch(function(e){ toast(e.message||'Failed','error'); }); }; });
      var ab = $('#addExpBtn'); if (ab) ab.onclick = openExperienceForm;
      var eb = $('#addEduBtn'); if (eb) eb.onclick = openEducationForm;
    }
    if (t === 'posts') loadProfilePosts(user.UserID);
  };

  $$('[data-prof-tab]').forEach(function(t){ t.onclick = function(){
    $$('[data-prof-tab]').forEach(function(x){ x.classList.remove('active'); });
    t.classList.add('active'); renderTab(t.getAttribute('data-prof-tab'));
  }; });
  renderTab('about');
  var editBtn = $('#editProfileBtn'); if (editBtn) editBtn.onclick = openEditProfileModal;
  if (!isMe) {
    var cb = $('#connBtn');
    if (cb) cb.onclick = async function(){
      var state = cb.getAttribute('data-state');
      cb.disabled = true;
      var action;
      if (state === 'connected') {
        if (!rel.connectionId) { toast('Connection id missing - refreshing', 'warn'); renderUserProfile(user.UserID); return; }
        if (!await confirmAction({title:'Remove this connection?',message:'You can send a new invitation later.',confirmLabel:'Remove'})) { cb.disabled = false; return; }
        action = api.respondConnection(rel.connectionId, 'remove').then(function(){ toast('Connection removed'); renderUserProfile(user.UserID); });
      } else if (state === 'incoming') {
        action = api.respondConnection(rel.connectionId, 'accept').then(function(){ toast('Connected'); refreshCounts(); renderUserProfile(user.UserID); });
      } else if (state === 'outgoing') {
        if (!await confirmAction({title:'Withdraw this invitation?',message:'Your pending invitation will be cancelled.',confirmLabel:'Withdraw'})) { cb.disabled = false; return; }
        action = api.respondConnection(rel.connectionId, 'cancel').then(function(){ toast('Request withdrawn'); refreshCounts(); renderUserProfile(user.UserID); });
      } else {
        action = api.sendConnection(user.UserID, '').then(function(){ toast('Connection request sent'); renderUserProfile(user.UserID); });
      }
      if (action) action.catch(function(e){ toast(e.message||'Failed', 'error'); }).then(function(){ cb.disabled = false; });
    };
    var fb = $('#followBtn'); if (fb) fb.onclick = function(){
      api.follow(user.UserID, !rel.following).then(function(){ toast(rel.following?'Unfollowed':'Following'); renderUserProfile(user.UserID); })
        .catch(function(e){ toast(e.message||'Failed', 'error'); });
    };
    var mb = $('#messageBtn'); if (mb) mb.onclick = function(){
      api.startConversation(user.UserID, '').then(function(r){
        location.hash = '#/messages';
        setTimeout(function(){ openConversation(r.data.conversationId); }, 200);
      }).catch(function(e){ toast(e.message||'Failed', 'error'); });
    };
    var mo = $('#moreProfileBtn'); if (mo) mo.onclick = function(){
      var dd = document.createElement('div');
      dd.className = 'dropdown';
      dd.innerHTML = '<button class="dropdown-item danger" data-act="block">' + (rel.blocked?'Unblock':'Block') + ' user</button>' +
        '<button class="dropdown-item danger" data-act="report">Report user</button>';
      document.body.appendChild(dd);
      var r = mo.getBoundingClientRect();
      dd.style.top = (r.bottom + window.scrollY + 4) + 'px';
      dd.style.left = (r.right - 200 + window.scrollX) + 'px';
      setTimeout(function(){ document.addEventListener('click', function(){ dd.remove(); }, {once:true}); }, 0);
      dd.onclick = function(ev){
        var aEl = ev.target.closest('[data-act]');
        var a = aEl ? aEl.getAttribute('data-act') : null;
        if (!a) return; dd.remove();
        if (a === 'block') { api.blockUser(user.UserID, !rel.blocked).then(function(){ toast(rel.blocked?'Unblocked':'Blocked'); renderUserProfile(user.UserID); }).catch(function(err){ toast(err.message||'Failed','error'); }); }
        if (a === 'report') openReportModal('User', user.UserID);
      };
    };
  }
}

function loadProfilePosts(userId){
  var el = $('#profilePosts'); if (!el) return;
  api.getUserPosts(userId).then(function(res){
    var list = res.data || [];
    el.innerHTML = list.length ? list.map(postCard).join('') : '<div class="empty"><p>No posts yet.</p></div>';
    bindCarousels();
  }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

function openEditProfileModal(){
  api.getMyProfile().then(function(res){
    var d = res.data;
    openModal({
      title:'Edit profile', size:'lg',
      body:'<div class="field"><label>First name</label><input class="input" id="epFirst" value="' + esc(d.user.FirstName) + '"></div>' +
        '<div class="field"><label>Last name</label><input class="input" id="epLast" value="' + esc(d.user.LastName) + '"></div>' +
        '<div class="field"><label>Professional headline</label><input class="input" id="epHeadline" value="' + esc(d.profile.Headline||'') + '"></div>' +
        '<div class="field"><label>About</label><textarea class="textarea" id="epAbout" rows="4">' + esc(d.profile.About||'') + '</textarea></div>' +
        '<div class="row"><div class="field"><label>City</label><input class="input" id="epCity" value="' + esc(d.profile.City||'') + '"></div>' +
          '<div class="field"><label>Region</label><input class="input" id="epRegion" value="' + esc(d.profile.Region||'') + '"></div></div>' +
        '<div class="field"><label>Website</label><input class="input" id="epWebsite" value="' + esc(d.profile.Website||'') + '"></div>' +
        '<div class="row"><div class="field"><label>Contact email</label><input class="input" id="epEmail" value="' + esc(d.profile.ContactEmail||'') + '"></div>' +
          '<div class="field"><label>Contact phone</label><input class="input" id="epPhone" value="' + esc(d.profile.ContactPhone||'') + '"></div></div>' +
        '<div class="field"><label>Languages</label><input class="input" id="epLanguages" value="' + esc(d.profile.Languages||'') + '"></div>' +
        '<div class="field"><label>Interests</label><input class="input" id="epInterests" value="' + esc(d.profile.Interests||'') + '"></div>' +
        '<div class="field"><label>Achievements</label><textarea class="textarea" id="epAchievements" rows="2">' + esc(d.profile.Achievements||'') + '</textarea></div>' +
        '<div class="row"><div class="field"><label>Profile visibility</label>' +
          '<select class="select" id="epProfileVis">' + ['Public','Connections','Private'].map(function(v){ return '<option ' + (d.profile.Visibility===v?'selected':'') + '>' + v + '</option>'; }).join('') + '</select></div>' +
          '<div class="field"><label>Contact visibility</label>' +
          '<select class="select" id="epContactVis">' + ['Public','Connections','Private'].map(function(v){ return '<option ' + (d.profile.ContactVisibility===v?'selected':'') + '>' + v + '</option>'; }).join('') + '</select></div></div>' +
        '<div class="field"><label>Profile photo</label><input type="file" id="epPhotoFile" accept="image/*" class="input"></div>' +
        '<div class="field"><label>Cover photo</label><input type="file" id="epCoverFile" accept="image/*" class="input"></div>',
      footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
        '<button class="btn btn-primary" id="epSave">Save profile</button>'
    });
    $('#epSave').onclick = function(){
      var btn = $('#epSave'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
      api.updateProfile({
        firstName: $('#epFirst').value.trim(), lastName: $('#epLast').value.trim(),
        headline: $('#epHeadline').value.trim(), about: $('#epAbout').value.trim(),
        city: $('#epCity').value.trim(), region: $('#epRegion').value.trim(),
        website: $('#epWebsite').value.trim(), contactEmail: $('#epEmail').value.trim(),
        contactPhone: $('#epPhone').value.trim(), languages: $('#epLanguages').value.trim(),
        interests: $('#epInterests').value.trim(), achievements: $('#epAchievements').value.trim(),
        profileVisibility: $('#epProfileVis').value, contactVisibility: $('#epContactVis').value
      }).then(function(){
        var up = function(input, kind, folder){
          var f = input.files[0]; if (!f) return Promise.resolve();
          if (f.size > 5*1024*1024) { toast('File too large', 'error'); return Promise.resolve(); }
          return api.uploadFile(folder, f)
            .then(function(u){ return api.uploadAvatar(kind, u.data.fileId); });
        };
        return up($('#epPhotoFile'), 'profile', 'Profile Photos').catch(function(){});
      }).then(function(){
        return (function(){
          var f = $('#epCoverFile').files[0]; if (!f) return Promise.resolve();
          if (f.size > 5*1024*1024) { toast('File too large', 'error'); return Promise.resolve(); }
          return api.uploadFile('Cover Photos', f)
            .then(function(u){ return api.uploadAvatar('cover', u.data.fileId); });
        })().catch(function(){});
      }).then(function(){
        closeAllModals(); toast('Profile updated');
        return bootstrap();
      }).then(function(){ renderMyProfile(); })
        .catch(function(e){ toast(e.message||'Failed', 'error'); btn.disabled = false; btn.textContent = 'Save profile'; });
    };
  }).catch(function(e){ toast(e.message||'Failed', 'error'); });
}

function openExperienceForm(){
  openModal({
    title:'Add experience', size:'sm',
    body:'<div class="field"><label>Job title *</label><input class="input" id="exTitle"></div>' +
      '<div class="field"><label>Company *</label><input class="input" id="exCompany"></div>' +
      '<div class="field"><label>Location</label><input class="input" id="exLocation"></div>' +
      '<div class="row"><div class="field"><label>Start date</label><input class="input" type="month" id="exStart"></div>' +
        '<div class="field"><label>End date</label><input class="input" type="month" id="exEnd"></div></div>' +
      '<label class="flex gap-2 small mb-3" style="cursor:pointer"><input type="checkbox" id="exCurrent"> Currently working here</label>' +
      '<div class="field"><label>Description</label><textarea class="textarea" id="exDesc" rows="3"></textarea></div>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="exSave">Save</button>'
  });
  $('#exSave').onclick = function(){
    var payload = {
      title: $('#exTitle').value.trim(), company: $('#exCompany').value.trim(),
      location: $('#exLocation').value.trim(), startDate: $('#exStart').value,
      endDate: $('#exEnd').value, current: $('#exCurrent').checked, description: $('#exDesc').value.trim()
    };
    if (!payload.title || !payload.company) { toast('Title and company required', 'error'); return; }
    api.addExperience(payload).then(function(){ closeAllModals(); toast('Added'); renderMyProfile(); })
      .catch(function(e){ toast(e.message||'Failed', 'error'); });
  };
}

function openEducationForm(){
  openModal({
    title:'Add education', size:'sm',
    body:'<div class="field"><label>School *</label><input class="input" id="edSchool"></div>' +
      '<div class="field"><label>Degree</label><input class="input" id="edDegree"></div>' +
      '<div class="field"><label>Field of study</label><input class="input" id="edField"></div>' +
      '<div class="row"><div class="field"><label>Start year</label><input class="input" id="edStart"></div>' +
        '<div class="field"><label>End year</label><input class="input" id="edEnd"></div></div>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="edSave">Save</button>'
  });
  $('#edSave').onclick = function(){
    var payload = {
      school: $('#edSchool').value.trim(), degree: $('#edDegree').value.trim(),
      field: $('#edField').value.trim(), startYear: $('#edStart').value.trim(),
      endYear: $('#edEnd').value.trim()
    };
    if (!payload.school) { toast('School required', 'error'); return; }
    api.addEducation(payload).then(function(){ closeAllModals(); toast('Added'); renderMyProfile(); })
      .catch(function(e){ toast(e.message||'Failed', 'error'); });
  };
}

export { renderMyProfile, renderUserProfile, renderProfileView, loadProfilePosts, openEditProfileModal, openExperienceForm, openEducationForm };
