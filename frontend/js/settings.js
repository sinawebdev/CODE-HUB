// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { shell } from './layout.js';
import { $, $$, State, closeModal, esc, openModal, setTheme, showCompletion, toast } from './core.js';
import { doLogout, renderLogin } from './auth.js';

function renderSettings(){
  shell('settings', { wide:true, noRail:true });
  $('#main').innerHTML =
    '<h1 class="mb-4">Settings</h1>' +
    '<div class="card card-pad mb-4">' +
      '<h3 class="mb-3">Change password</h3>' +
      '<div class="field"><label>Current password</label><input type="password" class="input" id="curPw"></div>' +
      '<div class="field"><label>New password</label><input type="password" class="input" id="newPw"></div>' +
      '<button class="btn btn-primary btn-sm" id="changePwBtn">Update password</button>' +
    '</div>' +
    '<div class="card card-pad mb-4">' +
      '<h3 class="mb-3">Appearance</h3>' +
      '<div class="flex gap-2" style="flex-wrap:wrap">' +
        ['light','dark','system'].map(function(t){ return '<button class="chip ' + (State.theme===t?'active':'') + '" data-theme-set="' + t + '">' + t.charAt(0).toUpperCase() + t.slice(1) + '</button>'; }).join('') +
      '</div>' +
    '</div>' +
    '<div class="card card-pad mb-4">' +
      '<h3 class="mb-3">Verification</h3>' +
      '<p class="small muted mb-3">Request a verified badge for your profile or company.</p>' +
      '<div class="flex gap-2" style="flex-wrap:wrap">' +
        '<button class="btn btn-secondary btn-sm" id="reqProfileVerify">Request profile verification</button>' +
      '</div>' +
    '</div>' +
    '<div class="card card-pad mb-4">' +
      '<h3 class="mb-3">Blocked users</h3>' +
      '<div id="blockedList"><div class="skeleton sk-line" style="width:50%"></div></div>' +
    '</div>' +
    '<div class="card card-pad mb-4">' +
      '<h3 class="mb-3">Account</h3>' +
      '<button class="btn btn-danger btn-sm" id="logoutSettingsBtn">Sign out</button>' +
    '</div>';
  $$('[data-theme-set]').forEach(function(b){ b.onclick = function(){ setTheme(b.getAttribute('data-theme-set')); renderSettings(); }; });
  $('#changePwBtn').onclick = function(){
    var cur = $('#curPw').value, np = $('#newPw').value;
    if (!cur || !np) { toast('Fill in both fields', 'error'); return; }
    if (np.length < 8) { toast('New password must be 8+ characters', 'error'); return; }
    api.changePassword(cur, np).then(function(){
      api.clearTokens(); window.dispatchEvent(new Event('kf:signed-out')); renderLogin();
      showCompletion('Password updated', 'Your new password is ready. Please sign in again to keep your account secure.');
    }).catch(function(e){ toast(e.message||'Failed', 'error'); });
  };
  $('#reqProfileVerify').onclick = function(){
    var dialog = openModal({ title:'Request profile verification',
      body:'<p class="confirmation-message mb-3">Our team will review your profile before adding a verified badge.</p><div class="field"><label>Note for the review team (optional)</label><textarea class="textarea" id="verificationNote" rows="4" placeholder="Add any details that help us verify your profile."></textarea></div>',
      footer:'<button class="btn btn-secondary" data-close>Cancel</button><button class="btn btn-primary" id="submitVerification">Submit request</button>'
    });
    $('#submitVerification', dialog).onclick = function(){
      var button = this;
      button.disabled = true;
      api.requestVerification('user', '', $('#verificationNote', dialog).value.trim()).then(function(){
        closeModal(dialog);
        showCompletion('Request submitted', 'Your profile is now waiting for review. We will notify you when a decision is made.');
      }).catch(function(e){ toast(e.message||'Failed', 'error'); button.disabled = false; });
    };
  };
  $('#logoutSettingsBtn').onclick = doLogout;
  api.getBlocked().then(function(r){
    var list = r.data || [];
    $('#blockedList').innerHTML = list.length ? list.map(function(b){
      return '<div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--border)"><div>' + esc(b.name) + '</div>' +
        '<button class="btn btn-ghost btn-xs" data-unblock="' + esc(b.userId) + '">Unblock</button></div>';
    }).join('') : '<p class="small muted">No blocked users.</p>';
    $$('[data-unblock]').forEach(function(b){ b.onclick = function(){
      api.blockUser(b.getAttribute('data-unblock'), false).then(function(){ toast('Unblocked'); renderSettings(); })
        .catch(function(e){ toast(e.message||'Failed', 'error'); });
    }; });
  }).catch(function(){});
}

export { renderSettings };
