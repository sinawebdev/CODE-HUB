// Ported from the original KoforLink demo; HTTP transport is in api.js.
import { State, __kfShowError, applyTheme, navigate } from './core.js';
import { doConnect } from './network.js';
import { openComposer } from './feed.js';
import { bootstrap, renderLogin, renderRegister, renderVerifyEmail, showLanding } from './auth.js';
import { router } from './router.js';
import { refreshCounts } from './layout.js';
import { rememberJobSearch } from './job-search-intent.js';

document.addEventListener('submit', function(e){
  if (e.target.id !== 'landingJobSearch') return;
  e.preventDefault();
  var fields = new FormData(e.target);
  rememberJobSearch(fields.get('query'), fields.get('city'));
  navigate('#/jobs');
});

window.addEventListener('kf:signed-out', function(){
  if(State.chatPoll) clearInterval(State.chatPoll);
  Object.assign(State, {user:null, emailVerified:false, profilePhoto:'', isStaff:false, isAdmin:false, currentChat:null, counts:{notifications:0,messages:0,connectionRequests:0}, cache:{}});
  navigate('#/login');
});
window.addEventListener('kf:verify-email', function(){ navigate('#/verify-email'); });

document.addEventListener('click', function(e){
  var section = e.target.closest('[data-section]');
  if (section) {
    e.preventDefault();
    var targetSection = document.getElementById(section.getAttribute('data-section'));
    if (targetSection) {
      targetSection.setAttribute('tabindex', '-1');
      targetSection.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
      targetSection.focus({ preventScroll: true });
    }
    return;
  }
  var g = e.target.closest('[data-goto]');
  if (g) {
    e.preventDefault();
    var target = g.getAttribute('data-goto');
    navigate(target);
    return;
  }
  var c = e.target.closest('[data-connect]');
  if (c) { e.preventDefault(); doConnect(c.getAttribute('data-connect'), c); return; }
  if (e.target.closest('[data-new-post]')) { e.preventDefault(); openComposer(); return; }
});

(function init(){
  try { applyTheme(); } catch (e) {}
  var y = document.getElementById('landFooterYear'); if (y) y.textContent = new Date().getFullYear();

  setTimeout(function(){
    if (!State.ready) { __kfShowError('The application is taking longer than expected.'); }
  }, 15000);

  (function run(){
    bootstrap().then(function(){
      try {
        if (!State.user) {
          var h = location.hash || '';
          if (h === '#/register') renderRegister();
          else if (h === '#/login') renderLogin();
          else if (h === '' || h === '#/' || h === '#') showLanding();
          else { location.hash = '#/login'; renderLogin(); }
          State.ready = true;
          return;
        }
        if (!State.emailVerified) {
          location.hash = '#/verify-email';
          renderVerifyEmail();
        } else {
          router();
        }
        State.ready = true;
        setInterval(refreshCounts, 30000);
      } catch (err) {
        console.error('[KoforLink] Startup render failed:', err);
        __kfShowError('Unable to initialize the application.');
        try { showLanding(); State.ready = true; } catch (e) {}
      }
    }).catch(function(err){
      console.error('[KoforLink] Bootstrap fatal:', err);
      try { showLanding(); State.ready = true; } catch (e) {}
    });
  })();
})();
