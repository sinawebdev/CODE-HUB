// Ported from the original KoforLink demo; HTTP transport is in api.js.
import { renderHome } from './home.js';
import { renderLogin, renderRegister, renderVerifyEmail, showLanding } from './auth.js';
import { renderNetwork } from './network.js';
import { renderJob, renderJobs, renderJobsNear, renderMyApplications, renderSaved } from './jobs.js';
import { renderCompanies, renderCompaniesNear, renderCompany, renderLocal } from './companies.js';
import { renderMessages } from './messages.js';
import { renderEvents } from './events.js';
import { renderNotifications } from './notifications.js';
import { renderMyProfile, renderUserProfile } from './profile.js';
import { renderSettings } from './settings.js';
import { renderSearch } from './search.js';
import { renderAdmin } from './admin.js';
import { renderPost } from './feed.js';
import { State, esc } from './core.js';

var Routes = {
  '#/': renderHome,
  '#/login': renderLogin,
  '#/register': renderRegister,
  '#/verify-email': renderVerifyEmail,
  '#/network': renderNetwork,
  '#/jobs': renderJobs,
  '#/jobs/near': renderJobsNear,
  '#/companies': renderCompanies,
  '#/companies/near': renderCompaniesNear,
  '#/local': renderLocal,
  '#/messages': renderMessages,
  '#/events': renderEvents,
  '#/notifications': renderNotifications,
  '#/profile': renderMyProfile,
  '#/settings': renderSettings,
  '#/saved': renderSaved,
  '#/applications': renderMyApplications,
  '#/search': renderSearch,
  '#/admin': renderAdmin,
  '#/company': renderCompany,
  '#/job': renderJob,
  '#/user': renderUserProfile,
  '#/post': renderPost
};

function router(){
  try {
    var hash = location.hash || '#/';
    var clean = hash.replace(/^#\/?/, '');
    var parts = clean ? clean.split('/') : [];
    var path = parts[0] || '';
    var key = '#/' + path;
    var param = parts.slice(1).join('/');

    var publicRoutes = ['#/login','#/register'];
    var authOnly = ['#/verify-email'];

    if (publicRoutes.indexOf(key) !== -1) {
      if (State.user) { location.hash = '#/'; return; }
    } else if (authOnly.indexOf(key) !== -1) {
      // Allow but enforce auth via bootstrap; renderVerifyEmail handles redirects.
    } else if (!State.user) {
      if (key !== '#/' && key !== '#') { location.hash = '#/login'; return; }
    }

    // Enforce email verification for authenticated users.
    if (State.user && !State.emailVerified && key !== '#/verify-email' && publicRoutes.indexOf(key) === -1) {
      location.hash = '#/verify-email';
      return;
    }
    if (State.user && State.emailVerified && key === '#/verify-email') {
      location.hash = '#/';
      return;
    }

    if (path === 'post' && param) return renderPost(param);
    if (path === 'job' && param) return renderJob(param);
    if (path === 'company' && param) return renderCompany(param);
    if (path === 'user' && param) return renderUserProfile(param);
    if (path === 'messages' && param) return renderMessages(param);
    if (path === 'jobs' && param === 'near') return renderJobsNear();
    if (path === 'companies' && param === 'near') return renderCompaniesNear();

    if (!State.user && (key === '#/' || key === '#' || path === '')) { showLanding(); return; }

    var fn = Routes[key] || renderHome;
    fn(param);
  } catch(err){
    console.error('[KoforLink] Router error:', err);
    var m = document.getElementById('main');
    if (m) m.innerHTML = '<div class="empty"><p>Something went wrong: ' + esc(err.message||err) + '</p></div>';
  }
}

window.addEventListener('hashchange', router);

export { Routes, router };
