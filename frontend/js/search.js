// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { shell, svgIcon } from './layout.js';
import { $, $$, debounce, esc } from './core.js';
import { personCard } from './network.js';
import { companyCard } from './companies.js';
import { jobCard } from './jobs.js';
import { bindCarousels, postCard } from './feed.js';
import { eventCard } from './events.js';

function renderSearch(){
  shell('search', { wide:true, noRail:true });
  $('#main').innerHTML =
    '<h1 class="mb-4">Search</h1>' +
    '<div class="card card-pad mb-4"><input class="input" id="globalSearch" placeholder="Search people, companies, jobs, posts, events, skills..."></div>' +
    '<div class="tabs">' +
      '<button class="tab active" data-search-type="all">All</button>' +
      '<button class="tab" data-search-type="people">People</button>' +
      '<button class="tab" data-search-type="companies">Companies</button>' +
      '<button class="tab" data-search-type="jobs">Jobs</button>' +
      '<button class="tab" data-search-type="posts">Posts</button>' +
      '<button class="tab" data-search-type="events">Events</button>' +
      '<button class="tab" data-search-type="skills">Skills</button>' +
    '</div>' +
    '<div id="searchResults"><div class="empty"><p>Start typing to search.</p></div></div>';
  var currentType = 'all';
  var doSearch = function(){
    var q = $('#globalSearch').value.trim();
    if (q.length < 2) { $('#searchResults').innerHTML = '<div class="empty"><p>Type at least 2 characters.</p></div>'; return; }
    var el = $('#searchResults');
    el.innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
    api.search(q, currentType).then(function(res){
      var d = res.data;
      var html = '';
      if (d.people.length) html += '<h3 class="mb-3">People (' + d.people.length + ')</h3><div class="grid grid-3 mb-4">' + d.people.map(function(p){ return personCard(p, 'connected'); }).join('') + '</div>';
      if (d.companies.length) html += '<h3 class="mb-3">Companies (' + d.companies.length + ')</h3><div class="grid grid-2 mb-4">' + d.companies.map(companyCard).join('') + '</div>';
      if (d.jobs.length) html += '<h3 class="mb-3">Jobs (' + d.jobs.length + ')</h3>' + d.jobs.map(jobCard).join('');
      if (d.posts.length) html += '<h3 class="mb-3 mt-4">Posts (' + d.posts.length + ')</h3>' + d.posts.map(postCard).join('');
      if (d.events.length) html += '<h3 class="mb-3 mt-4">Events (' + d.events.length + ')</h3>' + d.events.map(eventCard).join('');
      if (d.skills.length) html += '<h3 class="mb-3 mt-4">Skills (' + d.skills.length + ')</h3><div class="flex gap-2" style="flex-wrap:wrap">' + d.skills.map(function(s){ return '<span class="chip">' + esc(s.name) + '</span>'; }).join('') + '</div>';
      el.innerHTML = html || '<div class="empty"><div class="empty-icon">' + svgIcon('search') + '</div><h3>No results</h3><p>Try a different search term.</p></div>';
      bindCarousels();
    }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
  };
  $('#globalSearch').addEventListener('input', debounce(doSearch, 350));
  $$('[data-search-type]').forEach(function(t){ t.onclick = function(){
    $$('[data-search-type]').forEach(function(x){ x.classList.remove('active'); });
    t.classList.add('active'); currentType = t.getAttribute('data-search-type'); doSearch();
  }; });
  $('#globalSearch').focus();
}

export { renderSearch };
