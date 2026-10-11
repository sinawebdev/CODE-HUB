// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { authDestination } from './job-search-intent.js';
import { $, $$, State, closeAllModals, esc, hideBoot, labelFields, navigate, openModal, toast } from './core.js';

function showLanding(){
  hideBoot();
  $('#appShell').classList.add('hidden');
  $('#auth').classList.add('hidden');
  $('#landing').classList.remove('hidden');
  var y = $('#landFooterYear'); if (y) y.textContent = new Date().getFullYear();
}

function renderLogin(){
  if (State.user) { location.hash='#/'; return; }
  hideBoot();
  $('#landing').classList.add('hidden');
  $('#appShell').classList.add('hidden');
  $('#auth').classList.remove('hidden');
  $('#authCard').innerHTML =
    '<div class="auth-logo">' +
      '<div class="brand-mark">KL</div>' +
      '<h1>Welcome back</h1>' +
      '<p>Sign in to KoforLink and pick up where you left off.</p>' +
    '</div>' +
    '<form id="loginForm">' +
      '<div class="field"><label>Email</label><input type="email" name="email" class="input" placeholder="you@example.com" required autocomplete="email"></div>' +
      '<div class="field"><label>Password</label><input type="password" name="password" class="input" placeholder="Your password" required autocomplete="current-password"></div>' +
      '<div class="flex-between mb-4">' +
        '<label class="flex gap-2 small" style="cursor:pointer"><input type="checkbox" name="remember"> Remember me</label>' +
        '<a href="#" id="forgotLink" class="small" style="color:var(--brand);font-weight:600">Forgot password?</a>' +
      '</div>' +
      '<button type="submit" class="btn btn-primary btn-block btn-lg" id="loginBtn">Sign In</button>' +
    '</form>' +
    '<div class="auth-footer">New to KoforLink? <a href="#/register">Create an account</a></div>';
  labelFields($('#authCard'));
  $('#loginForm').onsubmit = function(ev){
    ev.preventDefault();
    var fd = new FormData(ev.target);
    var btn = $('#loginBtn'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    api.login(fd.get('email'), fd.get('password'), fd.get('remember') === 'on').then(function(res){
      api.setTokens(res.data.accessToken, res.data.refreshToken);
      State.user = res.data.user;
      State.emailVerified = !!res.data.emailVerified;
      toast('Welcome back, ' + res.data.user.FirstName + '!');
      return bootstrap();
    }).then(function(){
      if (State.user && !State.emailVerified) {
        navigate('#/verify-email');
      } else {
        navigate(authDestination());
      }
    }).catch(function(err){
      toast(err.message || 'Sign in failed', 'error');
      btn.disabled = false; btn.textContent = 'Sign In';
    });
  };
  $('#forgotLink').onclick = function(ev){ ev.preventDefault(); openPasswordResetModal(); };
}

function renderRegister(){
  if (State.user) { location.hash='#/'; return; }
  hideBoot();
  $('#landing').classList.add('hidden');
  $('#appShell').classList.add('hidden');
  $('#auth').classList.remove('hidden');
  $('#authCard').innerHTML =
    '<div class="auth-logo">' +
      '<div class="brand-mark">KL</div>' +
      '<h1>Join KoforLink</h1>' +
      '<p>Start with your details. Your next connection starts here.</p>' +
    '</div>' +
    '<form id="regForm">' +
      '<div class="row">' +
        '<div class="field"><label>First name</label><input class="input" name="firstName" required autocomplete="given-name"></div>' +
        '<div class="field"><label>Last name</label><input class="input" name="lastName" required autocomplete="family-name"></div>' +
      '</div>' +
      '<div class="field"><label>Email</label><input class="input" type="email" name="email" required autocomplete="email"></div>' +
      '<div class="field"><label>Phone</label><input class="input" name="phone" type="tel" autocomplete="tel" placeholder="+233 ..."></div>' +
      '<div class="row">' +
        '<div class="field"><label>City</label><input class="input" name="city" value="Koforidua"></div>' +
        '<div class="field"><label>Professional title</label><input class="input" name="professionalTitle" placeholder="e.g. Software Engineer"></div>' +
      '</div>' +
      '<div class="field"><label>I am a</label>' +
        '<select class="select" name="role">' +
          '<option value="Professional">Professional</option>' +
          '<option value="Student">Student</option>' +
          '<option value="Employer">Employer / Business</option>' +
          '<option value="Normal User">Normal user</option>' +
        '</select>' +
      '</div>' +
      '<div class="row">' +
        '<div class="field"><label>Password</label><input class="input" type="password" name="password" required minlength="8" autocomplete="new-password"></div>' +
        '<div class="field"><label>Confirm password</label><input class="input" type="password" name="confirmPassword" required minlength="8" autocomplete="new-password"></div>' +
      '</div>' +
      '<button type="submit" class="btn btn-primary btn-block btn-lg" id="regBtn">Create account</button>' +
    '</form>' +
    '<div class="auth-footer">Already have an account? <a href="#/login">Sign in</a></div>';
  labelFields($('#authCard'));
  $('#regForm').onsubmit = function(ev){
    ev.preventDefault();
    var fd = new FormData(ev.target);
    var payload = {};
    fd.forEach(function(v, k){ payload[k] = v; });
    if (payload.password !== payload.confirmPassword) return toast('Passwords do not match', 'error');
    var btn = $('#regBtn'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    api.register(payload).then(function(res){
      api.setTokens(res.data.accessToken, res.data.refreshToken);
      State.user = res.data.user;
      State.emailVerified = false;
      State.pendingEmail = res.data.email;
      toast('Account created — check your email');
      return bootstrap();
    }).then(function(){
      navigate('#/verify-email');
    }).catch(function(err){
      toast(err.message || 'Registration failed', 'error');
      btn.disabled = false; btn.textContent = 'Create account';
    });
  };
}

function renderVerifyEmail(){
  if (!State.user) { location.hash = '#/login'; return; }
  if (State.emailVerified) { location.hash = '#/'; return; }
  hideBoot();
  $('#landing').classList.add('hidden');
  $('#appShell').classList.add('hidden');
  $('#auth').classList.remove('hidden');

  var email = State.user.Email || State.pendingEmail || '';

  $('#authCard').innerHTML =
    '<div class="auth-logo">' +
      '<div class="brand-mark">' +
        '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:#fff">' +
          '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/></svg>' +
      '</div>' +
      '<h1>Verify your email</h1>' +
      '<p>We sent a 6-digit verification code to<br><b style="color:var(--text)">' + esc(email) + '</b></p>' +
    '</div>' +
    '<form id="otpForm" novalidate>' +
      '<div class="otp-wrap" id="otpWrap"></div>' +
      '<div id="otpError" class="field-error hidden" style="text-align:center;margin:8px 0 12px"></div>' +
      '<button type="submit" class="btn btn-primary btn-block btn-lg" id="verifyBtn">Verify email</button>' +
    '</form>' +
    '<div class="flex-between mt-4" style="font-size:13px">' +
      '<button type="button" class="btn btn-ghost btn-sm" id="resendBtn">Resend code</button>' +
      '<button type="button" class="btn btn-ghost btn-sm" id="changeEmailBtn">Change email</button>' +
    '</div>' +
    '<div class="auth-footer" style="margin-top:18px">' +
      'Wrong account? <a href="#" id="logoutFromVerify">Sign out</a>' +
    '</div>';

  // Build 6 OTP inputs
  var wrap = $('#otpWrap');
  wrap.innerHTML = Array(6).fill(0).map(function(_, i){
    return '<input class="otp-input" type="text" inputmode="numeric" autocomplete="one-time-code" ' +
      'maxlength="1" data-otp-idx="' + i + '" aria-label="Digit ' + (i+1) + '">';
  }).join('');

  var inputs = $$('.otp-input', wrap);
  function getCode(){ return inputs.map(function(i){ return i.value; }).join(''); }
  function setError(msg){
    var el = $('#otpError');
    if (msg) { el.textContent = msg; el.classList.remove('hidden'); inputs.forEach(function(i){ i.classList.add('error'); }); }
    else { el.textContent = ''; el.classList.add('hidden'); inputs.forEach(function(i){ i.classList.remove('error'); }); }
  }
  function focusIdx(i){ if (inputs[i]) inputs[i].focus(); }
  inputs.forEach(function(inp, i){
    inp.addEventListener('input', function(){
      inp.value = inp.value.replace(/\D/g,'').charAt(0);
      if (inp.value) { inp.classList.add('filled'); focusIdx(i+1); }
      else inp.classList.remove('filled');
      setError('');
      if (getCode().length === 6) { /* auto-submit optionally */ }
    });
    inp.addEventListener('keydown', function(e){
      if (e.key === 'Backspace' && !inp.value && i > 0) { focusIdx(i-1); return; }
      if (e.key === 'ArrowLeft' && i > 0) { e.preventDefault(); focusIdx(i-1); }
      if (e.key === 'ArrowRight' && i < inputs.length-1) { e.preventDefault(); focusIdx(i+1); }
      if (e.key === 'Enter') { e.preventDefault(); submit(); }
    });
    inp.addEventListener('paste', function(e){
      e.preventDefault();
      var txt = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g,'').slice(0, 6);
      if (!txt) return;
      for (var j = 0; j < 6; j++) {
        inputs[j].value = txt.charAt(j) || '';
        if (inputs[j].value) inputs[j].classList.add('filled');
      }
      focusIdx(Math.min(txt.length, 5));
      setError('');
    });
    inp.addEventListener('focus', function(){ inp.select && inp.select(); });
  });
  setTimeout(function(){ focusIdx(0); }, 200);

  function submit(){
    var code = getCode();
    if (code.length !== 6) return setError('Please enter all 6 digits.');
    var btn = $('#verifyBtn'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    api.verifyEmail(code).then(function(res){
      State.emailVerified = true;
      if (res.data && res.data.user) State.user = res.data.user;
      toast('Email verified successfully.');
      return bootstrap();
    }).then(function(){
      navigate(authDestination());
    }).catch(function(err){
      btn.disabled = false; btn.textContent = 'Verify email';
      setError(err.message || 'Verification failed');
      inputs.forEach(function(i){ i.value=''; i.classList.remove('filled'); });
      focusIdx(0);
    });
  }

  $('#otpForm').onsubmit = function(e){ e.preventDefault(); submit(); };

  $('#resendBtn').onclick = function(){
    var b = this;
    b.disabled = true;
    api.resendCode().then(function(){
      toast('A new code has been sent.');
      var wait = 60;
      var orig = b.textContent;
      b.textContent = 'Resend in ' + wait + 's';
      var t = setInterval(function(){
        wait--; b.textContent = 'Resend in ' + wait + 's';
        if (wait <= 0) { clearInterval(t); b.textContent = orig; b.disabled = false; }
      }, 1000);
    }).catch(function(e){
      b.disabled = false;
      toast(e.message || 'Could not resend', 'error');
    });
  };

  $('#changeEmailBtn').onclick = function(){
    openModal({
      title:'Change email', size:'sm',
      body:'<p class="small muted mb-3">Update the email address for this account. A new code will be sent to the new address.</p>' +
        '<input class="input" id="newEmail" aria-label="New email address" type="email" placeholder="you@example.com" value="' + esc(email) + '">',
      footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
        '<button class="btn btn-primary" id="saveNewEmail">Update email</button>'
    });
    $('#saveNewEmail').onclick = function(){
      var v = $('#newEmail').value.trim();
      if (!v) return toast('Enter an email', 'error');
      var btn = this; btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
      api.changeEmail(v).then(function(){
        closeAllModals();
        toast('Code sent to ' + v);
        State.pendingEmail = v;
        if (State.user) State.user.Email = v;
        renderVerifyEmail();
      }).catch(function(e){
        btn.disabled = false; btn.textContent = 'Update email';
        toast(e.message || 'Failed', 'error');
      });
    };
  };

  $('#logoutFromVerify').onclick = function(e){ e.preventDefault(); doLogout(); };
}

function doLogout(){
  api.logout().catch(function(){}).then(function(){
    api.clearTokens();
    State.user = null;
    State.emailVerified = false;
    location.hash = '#/login';
    location.reload();
  });
}

function bootstrap(){
  return api.bootstrap().then(function(res){
    State.settings = res.data.settings || {};
    State.counts = res.data.counts || State.counts;
    if (res.data.authenticated) {
      State.user = res.data.user;
      State.profilePhoto = res.data.profilePhoto || '';
      State.isStaff = !!res.data.isStaff;
      State.isAdmin = !!res.data.isAdmin;
      State.emailVerified = !!res.data.emailVerified;
    } else {
      State.user = null;
      State.emailVerified = false;
    }
    return res.data;
  }).catch(function(e){ console.error('[KoforLink] Bootstrap failed', e); return null; });
}

function openPasswordResetModal(){
  openModal({title:'Reset password',size:'sm',
    body:'<p class="muted small mb-3">Enter your email address and we will send a reset code.</p><input id="resetEmail" class="input" aria-label="Email address" type="email" placeholder="you@example.com">',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button><button class="btn btn-primary" id="resetBtn">Send code</button>'});
  $('#resetBtn').onclick = async function(){
    var email=$('#resetEmail').value.trim(), btn=this;
    if(!email) return toast('Enter your email','error');
    btn.disabled=true;
    try {
      await api.requestPasswordReset(email);
      closeAllModals();
      openModal({title:'Reset password',size:'sm',
        body:'<p class="muted small mb-3">Enter the code sent to your email and choose a new password.</p><div class="field"><label>Reset code</label><input id="resetCode" class="input" inputmode="numeric" maxlength="6" autocomplete="one-time-code"></div><div class="field"><label>New password</label><input id="resetPassword" class="input" type="password" minlength="8" autocomplete="new-password"></div>',
        footer:'<button class="btn btn-ghost" data-close>Cancel</button><button class="btn btn-primary" id="resetConfirm">Update password</button>'});
      $('#resetConfirm').onclick=async function(){
        var code=$('#resetCode').value.trim(), password=$('#resetPassword').value, confirm=this;
        if(!/^\d{6}$/.test(code))return toast('Enter the 6-digit code','error');
        if(password.length<8)return toast('Password must be at least 8 characters.','error');
        confirm.disabled=true;
        try{await api.confirmPasswordReset(email,code,password);toast('Password updated. You can now sign in.');closeAllModals();}
        catch(e){toast(e.message,'error');confirm.disabled=false;}
      };
    } catch(e){toast(e.message,'error');btn.disabled=false;}
  };
}


export { showLanding, renderLogin, renderRegister, renderVerifyEmail, doLogout, bootstrap, openPasswordResetModal };
