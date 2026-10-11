// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { shell, svgIcon } from './layout.js';
import { $, $$, closeAllModals, debounce, esc, openModal, timeAgo, toast, verifiedBadge } from './core.js';
import { openReportModal, postCard } from './feed.js';
import { consumeJobSearch } from './job-search-intent.js';

function renderJobs(){
  shell('jobs', { wide:true, noRail:true });
  $('#main').innerHTML =
    '<div class="flex-between mb-4" style="flex-wrap:wrap;gap:12px">' +
      '<div><h1>Jobs</h1><p class="muted">Discover opportunities across the Eastern Region and beyond.</p></div>' +
      '<div class="flex gap-2">' +
        '<button class="btn btn-secondary btn-sm" data-goto="#/jobs/near">Jobs near me</button>' +
        '<button class="btn btn-primary btn-sm" id="postJobBtn">+ Post a job</button>' +
      '</div>' +
    '</div>' +
    '<div class="card card-pad mb-4">' +
      '<div class="flex gap-3" style="flex-wrap:wrap">' +
        '<div class="job-filter-field" style="flex:1;min-width:200px"><label for="jobSearch">Search</label><input class="input" id="jobSearch" placeholder="Job title, skill or company"></div>' +
        '<div class="job-filter-field" style="flex:1;min-width:160px"><label for="jobCityFilter">Location</label><input class="input" id="jobCityFilter" placeholder="City or town"></div>' +
        '<div class="job-filter-field"><label for="jobTypeFilter">Employment type</label><select class="select" id="jobTypeFilter">' +
          '<option value="">All types</option><option>Full-time</option><option>Part-time</option><option>Contract</option><option>Internship</option><option>Freelance</option><option>Volunteer</option>' +
        '</select></div>' +
        '<div class="job-filter-field"><label for="jobArrangeFilter">Work arrangement</label><select class="select" id="jobArrangeFilter">' +
          '<option value="">Any arrangement</option><option>On-site</option><option>Remote</option><option>Hybrid</option>' +
        '</select></div>' +
      '</div>' +
    '</div>' +
    '<div id="jobsList"><div class="center-loader"><span class="spinner dark"></span></div></div>';
  $('#postJobBtn').onclick = openJobForm;
  var intent = consumeJobSearch();
  if (intent) { $('#jobSearch').value = intent.query; $('#jobCityFilter').value = intent.city; }
  $('#jobSearch').addEventListener('input', debounce(function(){ loadJobs(); }, 350));
  $('#jobCityFilter').addEventListener('input', debounce(function(){ loadJobs(); }, 350));
  $('#jobTypeFilter').onchange = loadJobs;
  $('#jobArrangeFilter').onchange = loadJobs;
  loadJobs();
}

function loadJobs(){
  var el = $('#jobsList'); if (!el) return;
  el.innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  api.getJobs({
    query: $('#jobSearch') ? $('#jobSearch').value : '',
    city: $('#jobCityFilter') ? $('#jobCityFilter').value : '',
    employmentType: $('#jobTypeFilter') ? $('#jobTypeFilter').value : '',
    workArrangement: $('#jobArrangeFilter') ? $('#jobArrangeFilter').value : '',
    limit: 60
  }).then(function(res){
    var jobs = res.data || [];
    el.innerHTML = jobs.length ? jobs.map(jobCard).join('')
      : '<div class="empty"><div class="empty-icon">' + svgIcon('briefcase') + '</div><h3>No jobs found</h3><p>Try different keywords or filters.</p></div>';
  }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

function jobCard(j){
  var logo = j.company && j.company.logo ? '<img src="' + esc(j.company.logo) + '" alt="">' : esc(((j.company && j.company.name) || 'J').charAt(0));
  var distance = (j.distance !== undefined && j.distance !== null) ? ' | <span style="color:var(--brand);font-weight:600">' + j.distance + ' km away</span>' : '';
  return '<div class="job-card" data-goto="#/job/' + esc(j.id) + '">' +
    '<div class="job-logo">' + logo + '</div>' +
    '<div class="job-main">' +
      '<div class="job-title">' + esc(j.title) + '</div>' +
      '<div class="job-company">' + esc((j.company && j.company.name) || '') + ((j.company && j.company.verified) ? ' ' + verifiedBadge() : '') + distance + '</div>' +
      '<div class="job-meta">' +
        '<span>' + esc(j.city||'') + '</span>' +
        '<span>' + esc(j.workArrangement||'') + '</span>' +
        '<span>' + esc(j.employmentType||'') + '</span>' +
        (j.salary ? '<span>' + esc(j.salary) + '</span>' : '') +
      '</div>' +
    '</div>' +
  '</div>';
}

function renderJobsNear(){
  shell('jobs', { wide:true, noRail:true });
  $('#main').innerHTML =
    '<div class="flex-between mb-4"><div><h1>Jobs Near Me</h1><p class="muted">Find opportunities close to you.</p></div>' +
      '<button class="btn btn-secondary btn-sm" data-goto="#/jobs">Back to all jobs</button></div>' +
    '<div class="card card-pad mb-4">' +
      '<div class="row">' +
        '<div class="field"><label>Your latitude</label><input class="input" id="myLat" placeholder="e.g. 6.0940"></div>' +
        '<div class="field"><label>Your longitude</label><input class="input" id="myLng" placeholder="e.g. -0.2591"></div>' +
      '</div>' +
      '<div class="row">' +
        '<div class="field"><label>Distance radius (km)</label><input class="input" id="radius" type="number" value="15"></div>' +
        '<div class="field" style="display:flex;align-items:flex-end"><button class="btn btn-secondary btn-block" id="useLocation">Use my location</button></div>' +
      '</div>' +
      '<button class="btn btn-primary btn-block" id="findNearby">Find jobs nearby</button>' +
    '</div>' +
    '<div id="nearJobs"></div>';
  $('#useLocation').onclick = function(){
    if (!navigator.geolocation) { toast('Geolocation not supported', 'error'); return; }
    navigator.geolocation.getCurrentPosition(
      function(pos){ $('#myLat').value = pos.coords.latitude.toFixed(5); $('#myLng').value = pos.coords.longitude.toFixed(5); toast('Location detected'); },
      function(){ toast('Unable to access location. Enter coordinates manually.', 'warn'); }
    );
  };
  $('#findNearby').onclick = function(){
    var lat = parseFloat($('#myLat').value), lng = parseFloat($('#myLng').value);
    var radius = parseFloat($('#radius').value) || 15;
    if (isNaN(lat)||isNaN(lng)) { toast('Enter latitude and longitude', 'error'); return; }
    var el = $('#nearJobs');
    el.innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
    api.jobsNearMe(lat, lng, radius, {}).then(function(res){
      var jobs = res.data || [];
      el.innerHTML = jobs.length ? jobs.map(jobCard).join('')
        : '<div class="empty"><div class="empty-icon">' + svgIcon('briefcase') + '</div><h3>No jobs within ' + radius + ' km</h3><p>Try increasing your radius.</p></div>';
    }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
  };
}

function renderJob(jobId){
  shell('jobs', { wide:true });
  $('#main').innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  api.getJob(jobId).then(function(res){
    var j = res.data;
    var logo = j.company && j.company.logo ? '<img src="' + esc(j.company.logo) + '" alt="">' : esc(((j.company && j.company.name) || 'J').charAt(0));
    var html = '<button class="btn btn-ghost btn-sm mb-3" data-goto="#/jobs">Back to jobs</button>' +
      '<div class="card card-pad">' +
        '<div class="flex gap-4" style="align-items:flex-start">' +
          '<div class="job-logo" style="width:64px;height:64px">' + logo + '</div>' +
          '<div style="flex:1;min-width:0">' +
            '<h1 style="font-size:22px">' + esc(j.title) + '</h1>' +
            '<div class="muted mt-2"><a href="#/company/' + esc((j.company && j.company.id)||'') + '" style="color:var(--brand);font-weight:600">' + esc((j.company && j.company.name)||'') + '</a>' + ((j.company && j.company.verified) ? ' ' + verifiedBadge() : '') + '</div>' +
            '<div class="job-meta mt-3" style="font-size:13px">' +
              '<span>' + esc(j.city||'') + '</span>' +
              '<span>' + esc(j.workArrangement||'') + '</span>' +
              '<span>' + esc(j.employmentType||'') + '</span>' +
              '<span>' + esc(j.experienceLevel||'') + '</span>' +
              (j.salary ? '<span>' + esc(j.salary) + '</span>' : '') +
            '</div>' +
          '</div>' +
        '</div>' +
        '<div class="flex gap-2 mt-4" style="flex-wrap:wrap">' +
          (j.applied
            ? '<button class="btn btn-secondary" disabled>Applied (' + esc(j.applicationStatus) + ')</button>'
            : '<button class="btn btn-primary" id="applyBtn">Apply now</button>') +
          '<button class="btn btn-secondary" id="saveJobBtn">' + (j.saved ? 'Saved' : 'Save job') + '</button>' +
          '<button class="btn btn-ghost" id="reportJob">Report</button>' +
        '</div>' +
      '</div>' +
      '<div class="card card-pad mt-4">' +
        '<h3 class="mb-3">Job description</h3>' +
        '<p style="white-space:pre-wrap;line-height:1.7">' + esc(j.description||'') + '</p>' +
        (j.responsibilities ? '<h3 class="mt-4 mb-3">Responsibilities</h3><p style="white-space:pre-wrap;line-height:1.7">' + esc(j.responsibilities) + '</p>' : '') +
        (j.requirements ? '<h3 class="mt-4 mb-3">Requirements</h3><p style="white-space:pre-wrap;line-height:1.7">' + esc(j.requirements) + '</p>' : '') +
        (j.skills && j.skills.length ? '<h3 class="mt-4 mb-3">Skills</h3><div class="flex gap-2" style="flex-wrap:wrap">' + j.skills.map(function(s){ return '<span class="chip">' + esc(s) + '</span>'; }).join('') + '</div>' : '') +
      '</div>';
    if (j.location) {
      var mapsQuery = [j.location.name, j.location.address, j.location.city].filter(Boolean).join(', ');
      html += '<div class="card card-pad mt-4">' +
        '<h3 class="mb-3">Workplace</h3>' +
        '<div class="loc-name">' + esc(j.location.name) + '</div>' +
        '<div class="loc-addr">' + esc([j.location.address, j.location.city, j.location.region].filter(Boolean).join(', ')) + '</div>' +
        '<div class="loc-actions">' +
          '<a class="btn btn-secondary btn-sm" target="_blank" href="https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(mapsQuery) + '">View on map</a>' +
          '<a class="btn btn-secondary btn-sm" target="_blank" href="https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(mapsQuery) + '">Get directions</a>' +
        '</div>' +
      '</div>';
    }
    $('#main').innerHTML = html;
    $('#saveJobBtn').onclick = function(){
      api.saveJob(jobId, !j.saved).then(function(r){
        j.saved = r.data.saved;
        $('#saveJobBtn').textContent = j.saved ? 'Saved' : 'Save job';
        toast(j.saved ? 'Job saved' : 'Removed');
      }).catch(function(e){ toast(e.message||'Failed', 'error'); });
    };
    var applyBtn = $('#applyBtn'); if (applyBtn) applyBtn.onclick = function(){ openApplyModal(jobId); };
    $('#reportJob').onclick = function(){ openReportModal('Job', jobId); };
  }).catch(function(e){ $('#main').innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed to load') + '</p></div>'; });
}

function openJobForm(){
  openModal({
    title:'Post a new job', size:'lg',
    body:'<div class="field"><label>Company</label><select class="select" id="jfCompany"></select></div>' +
      '<div class="field"><label>Job title *</label><input class="input" id="jfTitle"></div>' +
      '<div class="row">' +
        '<div class="field"><label>Employment type</label><select class="select" id="jfType"><option>Full-time</option><option>Part-time</option><option>Contract</option><option>Internship</option><option>Freelance</option><option>Volunteer</option></select></div>' +
        '<div class="field"><label>Work arrangement</label><select class="select" id="jfArrange"><option>On-site</option><option>Remote</option><option>Hybrid</option></select></div>' +
      '</div>' +
      '<div class="row">' +
        '<div class="field"><label>Experience level</label><select class="select" id="jfLevel"><option>Entry</option><option>Junior</option><option selected>Mid</option><option>Senior</option><option>Lead</option></select></div>' +
        '<div class="field"><label>Deadline</label><input class="input" type="date" id="jfDeadline"></div>' +
      '</div>' +
      '<div class="field"><label>Workplace location</label><select class="select" id="jfLocation"><option value="">Select a workplace</option></select></div>' +
      '<div class="field"><label>Skills (comma separated)</label><input class="input" id="jfSkills" placeholder="JavaScript, React, SQL"></div>' +
      '<div class="row"><div class="field"><label>Salary min</label><input class="input" type="number" id="jfSalaryMin"></div>' +
        '<div class="field"><label>Salary max</label><input class="input" type="number" id="jfSalaryMax"></div></div>' +
      '<div class="field"><label>Salary description</label><input class="input" id="jfSalary" placeholder="e.g. GHS 3,000 - 6,000 monthly"></div>' +
      '<div class="field"><label>Description *</label><textarea class="textarea" id="jfDesc" rows="4"></textarea></div>' +
      '<div class="field"><label>Responsibilities</label><textarea class="textarea" id="jfResp" rows="3"></textarea></div>' +
      '<div class="field"><label>Requirements</label><textarea class="textarea" id="jfReq" rows="3"></textarea></div>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="jfSubmit">Publish job</button>'
  });
  api.getMyCompanies().then(function(res){
    var list = res.data || [];
    var sel = $('#jfCompany');
    if (!list.length) { sel.innerHTML = '<option value="">You need a company first</option>'; $('#jfSubmit').disabled = true; }
    else {
      sel.innerHTML = list.map(function(c){ return '<option value="' + esc(c.id) + '">' + esc(c.name) + '</option>'; }).join('');
      loadLocationsForCompany(list[0].id);
      sel.onchange = function(){ loadLocationsForCompany(sel.value); };
    }
  }).catch(function(){});
  function loadLocationsForCompany(cid){
    var lsel = $('#jfLocation');
    lsel.innerHTML = '<option value="">Select workplace</option>';
    if (!cid) return;
    api.getCompany(cid).then(function(res){
      (res.data.locations||[]).forEach(function(l){
        lsel.insertAdjacentHTML('beforeend', '<option value="' + esc(l.id) + '">' + esc(l.name) + ' - ' + esc(l.city||'') + '</option>');
      });
    }).catch(function(){});
  }
  $('#jfSubmit').onclick = function(){
    var payload = {
      companyId: $('#jfCompany').value,
      title: $('#jfTitle').value.trim(),
      description: $('#jfDesc').value.trim(),
      responsibilities: $('#jfResp').value.trim(),
      requirements: $('#jfReq').value.trim(),
      skills: $('#jfSkills').value.trim(),
      salary: $('#jfSalary').value.trim(),
      salaryMin: $('#jfSalaryMin').value,
      salaryMax: $('#jfSalaryMax').value,
      employmentType: $('#jfType').value,
      experienceLevel: $('#jfLevel').value,
      deadline: $('#jfDeadline').value,
      workArrangement: $('#jfArrange').value,
      locationId: $('#jfLocation').value
    };
    if (!payload.title) { toast('Job title is required', 'error'); return; }
    if (!payload.companyId) { toast('Please select a company', 'error'); return; }
    var btn = $('#jfSubmit'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    api.createJob(payload).then(function(res){
      closeAllModals(); toast('Job published'); location.hash = '#/job/' + res.data.id;
    }).catch(function(e){ toast(e.message||'Failed', 'error'); btn.disabled = false; btn.textContent = 'Publish job'; });
  };
}

function openApplyModal(jobId){
  openModal({
    title:'Apply for this job',
    body:'<div class="field"><label>Cover letter (optional)</label><textarea class="textarea" id="applyLetter" rows="6" placeholder="Tell the employer why you are a good fit..."></textarea></div>' +
      '<div class="field"><label>Attach CV (optional, PDF/DOC)</label><input type="file" id="applyCV" accept=".pdf,.doc,.docx" class="input"><div class="field-hint">Max 5 MB</div></div>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="applySubmit">Submit application</button>'
  });
  var cvFileId = '';
  $('#applyCV').onchange = function(ev){
    var f = ev.target.files[0]; if (!f) return;
    if (f.size > 5*1024*1024) { toast('File too large', 'error'); return; }
    toast('Uploading CV...', 'warn');
    api.uploadFile('CVs', f)
      .then(function(res){ cvFileId = res.data.fileId; toast('CV uploaded'); })
      .catch(function(e){ toast(e.message||'Upload failed', 'error'); });
  };
  $('#applySubmit').onclick = function(){
    var letter = $('#applyLetter').value.trim();
    var btn = $('#applySubmit'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    api.applyJob(jobId, letter, cvFileId).then(function(){
      closeAllModals(); toast('Application submitted'); renderJob(jobId);
    }).catch(function(e){ toast(e.message||'Failed', 'error'); btn.disabled = false; btn.textContent = 'Submit application'; });
  };
}

function renderMyApplications(){
  shell('jobs', { wide:true });
  $('#main').innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  api.myApplications().then(function(res){
    var list = res.data || [];
    var html = '<div class="flex-between mb-4"><h1>My applications</h1><button class="btn btn-secondary btn-sm" data-goto="#/jobs">Browse jobs</button></div>';
    if (list.length) {
      html += list.map(function(a){
        return '<div class="card card-pad mb-3">' +
          '<div class="flex-between" style="flex-wrap:wrap;gap:10px">' +
            '<div>' +
              '<div style="font-weight:600"><a href="#/job/' + esc(a.job.id) + '" style="color:inherit">' + esc(a.job.title) + '</a></div>' +
              '<div class="small muted">' + esc((a.company && a.company.name)||'') + ' | ' + esc(a.job.city||'') + '</div>' +
            '</div>' +
            '<span class="badge ' + (a.status==='Hired'?'badge-success':a.status==='Rejected'?'badge-danger':'badge-brand') + '">' + esc(a.status) + '</span>' +
          '</div>' +
          '<div class="small muted mt-2">Applied ' + esc(a.timeAgo) + '</div>' +
        '</div>';
      }).join('');
    } else {
      html += '<div class="empty"><div class="empty-icon">' + svgIcon('briefcase') + '</div><h3>No applications yet</h3><p>Start applying to jobs that match your skills.</p></div>';
    }
    $('#main').innerHTML = html;
  }).catch(function(e){ $('#main').innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

function renderSaved(){
  shell('saved', { wide:true, noRail:true });
  $('#main').innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  Promise.all([
    api.getSavedPosts().catch(function(){ return { data: [] }; }),
    api.getSavedJobs().catch(function(){ return { data: [] }; })
  ]).then(function(results){
    var posts = results[0], jobs = results[1];
    $('#main').innerHTML =
      '<h1 class="mb-4">Saved</h1>' +
      '<div class="tabs">' +
        '<button class="tab active" data-saved-tab="posts">Saved posts (' + ((posts.data||[]).length) + ')</button>' +
        '<button class="tab" data-saved-tab="jobs">Saved jobs (' + ((jobs.data||[]).length) + ')</button>' +
      '</div>' +
      '<div id="savedContent"></div>';
    var render = function(tab){
      var el = $('#savedContent');
      if (tab === 'posts') {
        var l = posts.data || [];
        el.innerHTML = l.length ? l.map(postCard).join('') : '<div class="empty"><p>No saved posts.</p></div>';
      } else {
        var l2 = jobs.data || [];
        el.innerHTML = l2.length ? l2.map(jobCard).join('') : '<div class="empty"><p>No saved jobs.</p></div>';
      }
    };
    $$('[data-saved-tab]').forEach(function(t){ t.onclick = function(){
      $$('[data-saved-tab]').forEach(function(x){ x.classList.remove('active'); });
      t.classList.add('active'); render(t.getAttribute('data-saved-tab'));
    }; });
    render('posts');
  }).catch(function(e){ $('#main').innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

export { renderJobs, loadJobs, jobCard, renderJobsNear, renderJob, openJobForm, openApplyModal, renderMyApplications, renderSaved };
