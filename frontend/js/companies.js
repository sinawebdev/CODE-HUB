// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { shell, svgIcon } from './layout.js';
import { $, $$, avatar, closeAllModals, confirmAction, debounce, esc, openModal, toast, verifiedBadge } from './core.js';
import { jobCard } from './jobs.js';

function renderCompanies(){
  shell('companies', { wide:true, noRail:true });
  $('#main').innerHTML =
    '<div class="flex-between mb-4" style="flex-wrap:wrap;gap:12px">' +
      '<div><h1>Companies</h1><p class="muted">Discover businesses and organisations.</p></div>' +
      '<div class="flex gap-2">' +
        '<button class="btn btn-secondary btn-sm" data-goto="#/companies/near">Near me</button>' +
        '<button class="btn btn-primary btn-sm" id="createCompanyBtn">+ Create company page</button>' +
      '</div>' +
    '</div>' +
    '<div class="card card-pad mb-4"><input class="input" id="companySearch" placeholder="Search companies by name or industry..."></div>' +
    '<div id="companiesList"><div class="center-loader"><span class="spinner dark"></span></div></div>';
  $('#createCompanyBtn').onclick = openCompanyForm;
  $('#companySearch').addEventListener('input', debounce(function(){ loadCompanies(); }, 350));
  loadCompanies();
}

function loadCompanies(){
  var el = $('#companiesList'); if (!el) return;
  el.innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  api.getCompanies({ query: $('#companySearch') ? $('#companySearch').value : '', limit: 60 }).then(function(res){
    var list = res.data || [];
    el.innerHTML = list.length ? '<div class="grid grid-2">' + list.map(companyCard).join('') + '</div>'
      : '<div class="empty"><div class="empty-icon">' + svgIcon('building') + '</div><h3>No companies yet</h3><p>Be the first to create a company page.</p></div>';
  }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

function companyCard(c){
  var logo = c.logo ? '<img src="' + esc(c.logo) + '" alt="">' : esc((c.name||'C').charAt(0));
  return '<div class="card hoverable card-pad" data-goto="#/company/' + esc(c.id) + '" style="cursor:pointer">' +
    '<div class="flex gap-3">' +
      '<div class="job-logo">' + logo + '</div>' +
      '<div style="flex:1;min-width:0">' +
        '<div style="font-weight:600;font-size:15px" class="ellipsis">' + esc(c.name) + (c.verified ? ' ' + verifiedBadge() : '') + '</div>' +
        '<div class="small muted ellipsis">' + esc(c.industry||'') + '</div>' +
        '<div class="small muted mt-2">' + c.employeeCount + ' employees | ' + c.jobCount + ' open jobs</div>' +
      '</div>' +
    '</div>' +
    (c.hq ? '<div class="small muted mt-3">' + esc(c.hq.city||'') + ', ' + esc(c.hq.region||'') + '</div>' : '') +
  '</div>';
}

function renderCompaniesNear(){
  shell('companies', { wide:true, noRail:true });
  $('#main').innerHTML =
    '<div class="flex-between mb-4"><div><h1>Companies Near Me</h1><p class="muted">Discover businesses around you.</p></div>' +
      '<button class="btn btn-secondary btn-sm" data-goto="#/companies">Back to all companies</button></div>' +
    '<div class="card card-pad mb-4">' +
      '<div class="row">' +
        '<div class="field"><label>Latitude</label><input class="input" id="cnLat" placeholder="6.0940"></div>' +
        '<div class="field"><label>Longitude</label><input class="input" id="cnLng" placeholder="-0.2591"></div>' +
      '</div>' +
      '<div class="row">' +
        '<div class="field"><label>Radius (km)</label><input class="input" type="number" id="cnRadius" value="10"></div>' +
        '<div class="field" style="display:flex;align-items:flex-end"><button class="btn btn-secondary btn-block" id="cnUseLoc">Use my location</button></div>' +
      '</div>' +
      '<button class="btn btn-primary btn-block" id="cnFind">Find companies</button>' +
    '</div>' +
    '<div id="cnList"></div>';
  $('#cnUseLoc').onclick = function(){
    if (!navigator.geolocation) { toast('Geolocation unavailable', 'error'); return; }
    navigator.geolocation.getCurrentPosition(function(p){
      $('#cnLat').value = p.coords.latitude.toFixed(5);
      $('#cnLng').value = p.coords.longitude.toFixed(5);
      toast('Location detected');
    }, function(){ toast('Location denied - enter manually', 'warn'); });
  };
  $('#cnFind').onclick = function(){
    var lat = parseFloat($('#cnLat').value), lng = parseFloat($('#cnLng').value);
    var r = parseFloat($('#cnRadius').value) || 10;
    if (isNaN(lat)||isNaN(lng)) { toast('Enter coordinates', 'error'); return; }
    var el = $('#cnList');
    el.innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
    api.nearbyCompanies(lat, lng, r).then(function(res){
      var list = res.data || [];
      if (list.length) {
        el.innerHTML = '<div class="grid grid-2">' + list.map(function(c){
          var logo = c.logo ? '<img src="' + esc(c.logo) + '" alt="">' : esc((c.name||'C').charAt(0));
          return '<div class="card hoverable card-pad" data-goto="#/company/' + esc(c.id) + '" style="cursor:pointer">' +
            '<div class="flex gap-3">' +
              '<div class="job-logo">' + logo + '</div>' +
              '<div style="flex:1;min-width:0">' +
                '<div style="font-weight:600" class="ellipsis">' + esc(c.name) + (c.verified?' ' + verifiedBadge():'') + '</div>' +
                '<div class="small muted">' + esc(c.industry||'') + '</div>' +
                '<div class="badge badge-brand mt-2">' + c.distance + ' km away</div>' +
              '</div>' +
            '</div>' +
          '</div>';
        }).join('') + '</div>';
      } else { el.innerHTML = '<div class="empty"><p>No companies within ' + r + ' km.</p></div>'; }
    }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
  };
}

function renderCompany(companyId){
  shell('companies', { wide:true });
  $('#main').innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  api.getCompany(companyId).then(function(res){
    var c = res.data;
    var cover = c.cover ? '<img src="' + esc(c.cover) + '" alt="">' : '';
    var logo = c.logo ? '<img src="' + esc(c.logo) + '" alt="">' : esc((c.name||'C').charAt(0));
    var html = '<div class="card" style="overflow:hidden">' +
      '<div class="profile-cover" style="height:160px">' + cover + '<div class="profile-cover-overlay"></div></div>' +
      '<div style="padding:0 24px 20px;position:relative">' +
        '<div style="margin-top:-40px;position:relative;display:inline-block">' +
          '<div class="job-logo" style="width:80px;height:80px;border:4px solid var(--surface);background:var(--surface)">' + logo + '</div>' +
        '</div>' +
        '<h1 class="mt-3" style="font-size:24px">' + esc(c.name) + (c.verified ? ' ' + verifiedBadge() : '') + '</h1>' +
        '<div class="muted mt-2">' + esc(c.industry||'') + (c.size ? ' | ' + esc(c.size) + ' employees' : '') + '</div>' +
        (c.hq ? '<div class="small muted mt-2">' + esc(c.hq.city||'') + ', ' + esc(c.hq.region||'') + '</div>' : '') +
        '<div class="flex gap-2 mt-4" style="flex-wrap:wrap">' +
          (c.website ? '<a class="btn btn-secondary btn-sm" target="_blank" href="' + esc(c.website) + '">Website</a>' : '') +
          (c.canManage ? '<button class="btn btn-primary btn-sm" id="editCompanyBtn">Edit page</button>' +
            '<button class="btn btn-secondary btn-sm" id="addLocationBtn">+ Add workplace</button>' : '') +
        '</div>' +
      '</div>' +
    '</div>' +
    '<div class="tabs mt-4">' +
      '<button class="tab active" data-co-tab="about">About</button>' +
      '<button class="tab" data-co-tab="jobs">Jobs (' + c.jobs.length + ')</button>' +
      '<button class="tab" data-co-tab="locations">Workplaces (' + c.locations.length + ')</button>' +
      '<button class="tab" data-co-tab="employees">People (' + c.members.length + ')</button>' +
      (c.services.length ? '<button class="tab" data-co-tab="services">Services</button>' : '') +
    '</div>' +
    '<div id="coContent"></div>';
    $('#main').innerHTML = html;
    var tabs = {
      about: function(){
        return '<div class="card card-pad">' +
          '<h3 class="mb-3">About ' + esc(c.name) + '</h3>' +
          '<p style="white-space:pre-wrap;line-height:1.7">' + esc(c.description||'No description yet.') + '</p>' +
          ((c.email||c.phone) ? '<div class="divider"></div><div class="grid grid-2">' +
            (c.email ? '<div><div class="small muted">Email</div><div class="bold">' + esc(c.email) + '</div></div>' : '') +
            (c.phone ? '<div><div class="small muted">Phone</div><div class="bold">' + esc(c.phone) + '</div></div>' : '') +
          '</div>' : '') +
        '</div>';
      },
      jobs: function(){ return c.jobs.length ? c.jobs.map(jobCard).join('') : '<div class="empty"><p>No open positions right now.</p></div>'; },
      locations: function(){
        if (!c.locations.length) return '<div class="empty"><p>No workplaces added yet.</p></div>';
        var h = (c.canManage ? '<button class="btn btn-primary btn-sm mb-3" id="addLocationBtn2">+ Add workplace</button>' : '') +
          c.locations.map(locBlock).join('');
        return h;
      },
      employees: function(){
        if (!c.members.length) return '<div class="empty"><p>No team members listed.</p></div>';
        return '<div class="grid grid-3">' + c.members.map(function(m){
          return '<div class="card card-pad" style="text-align:center">' +
            '<a href="#/user/' + esc(m.userId) + '">' + avatar(m.photo, m.name, '56') + '</a>' +
            '<div style="font-weight:600;margin-top:8px"><a href="#/user/' + esc(m.userId) + '" style="color:inherit">' + esc(m.name) + '</a>' + (m.verified ? ' ' + verifiedBadge() : '') + '</div>' +
            '<div class="small muted">' + esc(m.title||m.role) + '</div>' +
          '</div>';
        }).join('') + '</div>';
      },
      services: function(){
        return '<div class="grid grid-2">' + c.services.map(function(s){
          return '<div class="card card-pad"><h4>' + esc(s.name) + '</h4><p class="small muted mt-2">' + esc(s.description||'') + '</p></div>';
        }).join('') + '</div>';
      }
    };
    var renderTab = function(t){
      $('#coContent').innerHTML = tabs[t] ? tabs[t]() : '';
      if (t === 'locations' && c.canManage) {
        var b = $('#addLocationBtn2'); if (b) b.onclick = function(){ openLocationForm(companyId, null); };
        $$('[data-del-loc]').forEach(function(x){ x.onclick = async function(ev){
          ev.stopPropagation();
          if (!await confirmAction({ title:'Delete this workplace?', message:'This workplace will be removed from the company profile.' })) return;
          api.deleteLocation(x.getAttribute('data-del-loc')).then(function(){ toast('Deleted'); renderCompany(companyId); })
            .catch(function(e){ toast(e.message||'Failed', 'error'); });
        }; });
        $$('[data-edit-loc]').forEach(function(x){ x.onclick = function(ev){
          ev.stopPropagation();
          var id = x.getAttribute('data-edit-loc');
          var loc = null;
          for (var i=0;i<c.locations.length;i++) { if (c.locations[i].id===id) { loc = c.locations[i]; break; } }
          openLocationForm(companyId, loc);
        }; });
        $$('[data-add-photo]').forEach(function(x){ x.onclick = function(ev){
          ev.stopPropagation();
          openLocationPhotoUpload(x.getAttribute('data-add-photo'), companyId);
        }; });
      }
    };
    $$('[data-co-tab]').forEach(function(t){ t.onclick = function(){
      $$('[data-co-tab]').forEach(function(x){ x.classList.remove('active'); });
      t.classList.add('active'); renderTab(t.getAttribute('data-co-tab'));
    }; });
    renderTab('about');
    var editBtn = $('#editCompanyBtn'); if (editBtn) editBtn.onclick = function(){ openEditCompanyForm(c); };
    var addLoc = $('#addLocationBtn'); if (addLoc) addLoc.onclick = function(){ openLocationForm(companyId, null); };
  }).catch(function(e){ $('#main').innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

function locBlock(l){
  return '<div class="loc-card">' +
    '<div class="flex-between" style="flex-wrap:wrap;gap:10px">' +
      '<div style="flex:1;min-width:0">' +
        '<div class="loc-name">' + esc(l.name) + (l.isHQ ? ' <span class="badge badge-brand">HQ</span>' : '') + '</div>' +
        '<div class="loc-addr">' + esc([l.address, l.area, l.city, l.region, l.country].filter(Boolean).join(', ')) + '</div>' +
        (l.ghanaPostGps ? '<div class="small muted mt-2">GhanaPost GPS: <b>' + esc(l.ghanaPostGps) + '</b></div>' : '') +
        (l.landmark ? '<div class="small muted">Landmark: ' + esc(l.landmark) + '</div>' : '') +
        (l.phone ? '<div class="small muted">Phone: ' + esc(l.phone) + '</div>' : '') +
        (l.openingTime ? '<div class="small muted">Open: ' + esc(l.openingTime) + ' - ' + esc(l.closingTime) + '</div>' : '') +
      '</div>' +
    '</div>' +
    '<div class="loc-actions">' +
      '<a class="btn btn-secondary btn-sm" target="_blank" href="' + esc(l.mapsLink) + '">View on map</a>' +
      '<a class="btn btn-secondary btn-sm" target="_blank" href="' + esc(l.directionsLink) + '">Get directions</a>' +
      '<button class="btn btn-ghost btn-sm" data-edit-loc="' + esc(l.id) + '">Edit</button>' +
      '<button class="btn btn-ghost btn-sm" data-add-photo="' + esc(l.id) + '">+ Photo</button>' +
      '<button class="btn btn-ghost btn-sm" style="color:var(--danger)" data-del-loc="' + esc(l.id) + '">Delete</button>' +
    '</div>' +
    (l.photos.length ? '<div class="loc-gallery">' + l.photos.map(function(p){ return '<img src="' + esc(p.url) + '" alt="' + esc(p.caption||'') + '" loading="lazy">'; }).join('') + '</div>' : '') +
  '</div>';
}

function openCompanyForm(){
  openModal({
    title:'Create company page',
    body:'<div class="field"><label>Company name *</label><input class="input" id="cfName"></div>' +
      '<div class="field"><label>Industry</label><input class="input" id="cfIndustry" placeholder="e.g. Information Technology"></div>' +
      '<div class="row"><div class="field"><label>Email</label><input class="input" id="cfEmail" type="email"></div>' +
        '<div class="field"><label>Phone</label><input class="input" id="cfPhone"></div></div>' +
      '<div class="row"><div class="field"><label>Website</label><input class="input" id="cfWebsite"></div>' +
        '<div class="field"><label>Founded</label><input class="input" id="cfFounded" placeholder="2018"></div></div>' +
      '<div class="field"><label>Company size</label><select class="select" id="cfSize"><option value="">Select</option><option>1-10</option><option>11-50</option><option>51-200</option><option>201-500</option><option>500+</option></select></div>' +
      '<div class="field"><label>Your title at the company</label><input class="input" id="cfYourTitle" placeholder="e.g. Founder"></div>' +
      '<div class="field"><label>Description</label><textarea class="textarea" id="cfDesc" rows="5"></textarea></div>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="cfSubmit">Create page</button>'
  });
  $('#cfSubmit').onclick = function(){
    var payload = {
      name: $('#cfName').value.trim(),
      industry: $('#cfIndustry').value.trim(),
      email: $('#cfEmail').value.trim(),
      phone: $('#cfPhone').value.trim(),
      website: $('#cfWebsite').value.trim(),
      founded: $('#cfFounded').value.trim(),
      size: $('#cfSize').value,
      yourTitle: $('#cfYourTitle').value.trim(),
      description: $('#cfDesc').value.trim()
    };
    if (!payload.name) { toast('Company name is required', 'error'); return; }
    var btn = $('#cfSubmit'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    api.createCompany(payload).then(function(res){
      closeAllModals(); toast('Company page created'); location.hash = '#/company/' + res.data.id;
    }).catch(function(e){ toast(e.message||'Failed', 'error'); btn.disabled = false; btn.textContent = 'Create page'; });
  };
}

function openEditCompanyForm(c){
  openModal({
    title:'Edit company page',
    body:'<div class="field"><label>Company name</label><input class="input" id="ecfName" value="' + esc(c.name) + '"></div>' +
      '<div class="field"><label>Industry</label><input class="input" id="ecfIndustry" value="' + esc(c.industry||'') + '"></div>' +
      '<div class="row"><div class="field"><label>Email</label><input class="input" id="ecfEmail" value="' + esc(c.email||'') + '"></div>' +
        '<div class="field"><label>Phone</label><input class="input" id="ecfPhone" value="' + esc(c.phone||'') + '"></div></div>' +
      '<div class="row"><div class="field"><label>Website</label><input class="input" id="ecfWebsite" value="' + esc(c.website||'') + '"></div>' +
        '<div class="field"><label>Founded</label><input class="input" id="ecfFounded" value="' + esc(c.founded||'') + '"></div></div>' +
      '<div class="field"><label>Company size</label><select class="select" id="ecfSize"><option value="">Select</option>' +
        ['1-10','11-50','51-200','201-500','500+'].map(function(s){ return '<option ' + (c.size===s?'selected':'') + '>' + s + '</option>'; }).join('') +
      '</select></div>' +
      '<div class="field"><label>Description</label><textarea class="textarea" id="ecfDesc" rows="5">' + esc(c.description||'') + '</textarea></div>' +
      '<div class="field"><label>Logo</label><input type="file" id="ecfLogo" accept="image/*" class="input"></div>' +
      '<div class="field"><label>Cover photo</label><input type="file" id="ecfCover" accept="image/*" class="input"></div>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="ecfSubmit">Save</button>'
  });
  var uploadAndSet = function(input, kind){
    var f = input.files[0]; if (!f) return Promise.resolve();
    if (f.size > 5*1024*1024) { toast('File too large', 'error'); return Promise.resolve(); }
    toast('Uploading...', 'warn');
    return api.uploadFile(kind === 'cover' ? 'Company Photos' : 'Company Logos', f).then(function(up){
      return api.uploadCompanyImage(c.id, kind, up.data.fileId);
    });
  };
  $('#ecfSubmit').onclick = function(){
    var payload = {
      name: $('#ecfName').value.trim(),
      industry: $('#ecfIndustry').value.trim(),
      email: $('#ecfEmail').value.trim(),
      phone: $('#ecfPhone').value.trim(),
      website: $('#ecfWebsite').value.trim(),
      founded: $('#ecfFounded').value.trim(),
      size: $('#ecfSize').value,
      description: $('#ecfDesc').value.trim()
    };
    var btn = $('#ecfSubmit'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    api.updateCompany(c.id, payload).then(function(){
      return uploadAndSet($('#ecfLogo'), 'logo').catch(function(){});
    }).then(function(){
      return uploadAndSet($('#ecfCover'), 'cover').catch(function(){});
    }).then(function(){
      closeAllModals(); toast('Company updated'); renderCompany(c.id);
    }).catch(function(e){ toast(e.message||'Failed', 'error'); btn.disabled = false; btn.textContent = 'Save'; });
  };
}

function openLocationForm(companyId, loc){
  var isEdit = !!loc;
  openModal({
    title: isEdit ? 'Edit workplace' : 'Add workplace', size:'lg',
    body:'<div class="field"><label>Workplace name *</label><input class="input" id="lfName" value="' + esc((loc&&loc.name)||'') + '" placeholder="e.g. Koforidua Head Office"></div>' +
      '<div class="field"><label>Address</label><input class="input" id="lfAddress" value="' + esc((loc&&loc.address)||'') + '"></div>' +
      '<div class="row"><div class="field"><label>City / Town</label><input class="input" id="lfCity" value="' + esc((loc&&loc.city)||'Koforidua') + '"></div>' +
        '<div class="field"><label>Region</label><input class="input" id="lfRegion" value="' + esc((loc&&loc.region)||'Eastern Region') + '"></div></div>' +
      '<div class="row"><div class="field"><label>Area</label><input class="input" id="lfArea" value="' + esc((loc&&loc.area)||'') + '"></div>' +
        '<div class="field"><label>Country</label><input class="input" id="lfCountry" value="' + esc((loc&&loc.country)||'Ghana') + '"></div></div>' +
      '<div class="row"><div class="field"><label>GhanaPost GPS</label><input class="input" id="lfGps" value="' + esc((loc&&loc.ghanaPostGps)||'') + '" placeholder="e.g. EN-0123-4567"></div>' +
        '<div class="field"><label>Landmark</label><input class="input" id="lfLandmark" value="' + esc((loc&&loc.landmark)||'') + '"></div></div>' +
      '<div class="row"><div class="field"><label>Latitude</label><input class="input" id="lfLat" value="' + (loc?.latitude ?? '') + '"></div>' +
        '<div class="field"><label>Longitude</label><input class="input" id="lfLng" value="' + (loc?.longitude ?? '') + '"></div></div>' +
      '<button type="button" class="btn btn-secondary btn-sm mb-3" id="lfDetect">Detect from current location</button>' +
      '<div class="row"><div class="field"><label>Phone</label><input class="input" id="lfPhone" value="' + esc((loc&&loc.phone)||'') + '"></div>' +
        '<div class="field"><label>Email</label><input class="input" id="lfEmail" value="' + esc((loc&&loc.email)||'') + '"></div></div>' +
      '<div class="row"><div class="field"><label>Opening time</label><input class="input" id="lfOpen" value="' + esc((loc&&loc.openingTime)||'08:00') + '"></div>' +
        '<div class="field"><label>Closing time</label><input class="input" id="lfClose" value="' + esc((loc&&loc.closingTime)||'17:00') + '"></div></div>' +
      '<label class="flex gap-2 small" style="cursor:pointer"><input type="checkbox" id="lfHQ" ' + ((loc&&loc.isHQ)?'checked':'') + '> Mark as headquarters</label>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="lfSubmit">' + (isEdit ? 'Save changes' : 'Add workplace') + '</button>'
  });
  $('#lfDetect').onclick = function(){
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(function(p){
        $('#lfLat').value = p.coords.latitude.toFixed(6);
        $('#lfLng').value = p.coords.longitude.toFixed(6);
        toast('Coordinates detected');
      }, function(){ toast('Location denied', 'warn'); });
    } else { toast('Geolocation unavailable', 'warn'); }
  };
  $('#lfSubmit').onclick = function(){
    var payload = {
      name: $('#lfName').value.trim(), address: $('#lfAddress').value.trim(),
      city: $('#lfCity').value.trim(), region: $('#lfRegion').value.trim(),
      area: $('#lfArea').value.trim(), country: $('#lfCountry').value.trim(),
      ghanaPostGps: $('#lfGps').value.trim(), landmark: $('#lfLandmark').value.trim(),
      latitude: $('#lfLat').value ? parseFloat($('#lfLat').value) : null,
      longitude: $('#lfLng').value ? parseFloat($('#lfLng').value) : null,
      phone: $('#lfPhone').value.trim(), email: $('#lfEmail').value.trim(),
      openingTime: $('#lfOpen').value.trim(), closingTime: $('#lfClose').value.trim(),
      isHQ: $('#lfHQ').checked
    };
    if (!payload.name) { toast('Workplace name is required', 'error'); return; }
    var btn = $('#lfSubmit'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    var p = isEdit ? api.updateLocation(loc.id, payload) : api.addLocation(companyId, payload);
    p.then(function(){ closeAllModals(); toast(isEdit ? 'Workplace updated' : 'Workplace added'); renderCompany(companyId); })
      .catch(function(e){ toast(e.message||'Failed', 'error'); btn.disabled = false; btn.textContent = isEdit ? 'Save changes' : 'Add workplace'; });
  };
}

function openLocationPhotoUpload(locationId, companyId){
  openModal({
    title:'Add workplace photo', size:'sm',
    body:'<div class="field"><label>Category</label><select class="select" id="lpCat"><option>Building</option><option>Reception</option><option>Office</option><option>Shop</option><option>Factory</option><option>Work environment</option><option>Signboard</option></select></div>' +
      '<div class="field"><label>Caption</label><input class="input" id="lpCap"></div>' +
      '<div class="field"><label>Photo</label><input type="file" id="lpFile" accept="image/*" class="input"></div>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="lpSubmit">Upload</button>'
  });
  $('#lpSubmit').onclick = function(){
    var f = $('#lpFile').files[0];
    if (!f) { toast('Select a photo', 'error'); return; }
    if (f.size > 5*1024*1024) { toast('File too large', 'error'); return; }
    var btn = $('#lpSubmit'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    api.uploadFile('Workplace Photos', f)
      .then(function(up){ return api.addLocationPhoto(locationId, up.data.fileId, $('#lpCat').value, $('#lpCap').value.trim()); })
      .then(function(){ closeAllModals(); toast('Photo added'); renderCompany(companyId); })
      .catch(function(e){ toast(e.message||'Failed', 'error'); btn.disabled = false; btn.textContent = 'Upload'; });
  };
}

function renderLocal(){
  shell('local', { wide:true, noRail:true });
  $('#main').innerHTML =
    '<h1>KoforLink Local</h1>' +
    '<p class="muted mb-4">Your gateway to opportunities across Koforidua, the Eastern Region and Ghana.</p>' +
    '<div class="grid grid-2 mb-4">' +
      '<div class="card hoverable card-pad" data-goto="#/jobs" style="cursor:pointer"><div class="flex gap-3"><div class="land-feature-icon" style="margin:0">' + svgIcon('briefcase') + '</div><div><h3>Jobs</h3><p class="small muted">Find employment near you.</p></div></div></div>' +
      '<div class="card hoverable card-pad" data-goto="#/companies" style="cursor:pointer"><div class="flex gap-3"><div class="land-feature-icon" style="margin:0">' + svgIcon('building') + '</div><div><h3>Companies</h3><p class="small muted">Discover verified employers.</p></div></div></div>' +
      '<div class="card hoverable card-pad" data-goto="#/companies/near" style="cursor:pointer"><div class="flex gap-3"><div class="land-feature-icon" style="margin:0">' + svgIcon('map') + '</div><div><h3>Workplaces Near Me</h3><p class="small muted">Explore businesses around you.</p></div></div></div>' +
      '<div class="card hoverable card-pad" data-goto="#/events" style="cursor:pointer"><div class="flex gap-3"><div class="land-feature-icon" style="margin:0">' + svgIcon('calendar') + '</div><div><h3>Events</h3><p class="small muted">Career fairs, workshops and more.</p></div></div></div>' +
      '<div class="card hoverable card-pad" data-goto="#/network" style="cursor:pointer"><div class="flex gap-3"><div class="land-feature-icon" style="margin:0">' + svgIcon('network') + '</div><div><h3>Professionals</h3><p class="small muted">Connect with people nearby.</p></div></div></div>' +
      '<div class="card hoverable card-pad" data-goto="#/search" style="cursor:pointer"><div class="flex gap-3"><div class="land-feature-icon" style="margin:0">' + svgIcon('search') + '</div><div><h3>Search everything</h3><p class="small muted">Find people, jobs and more.</p></div></div></div>' +
    '</div>' +
    '<div class="card card-pad"><h3 class="mb-3">Nearby workplaces</h3>' +
      '<button class="btn btn-primary btn-sm" id="localNear">Use my location</button>' +
      '<div id="localNearList" class="mt-3"></div>' +
    '</div>';
  $('#localNear').onclick = function(){
    if (!navigator.geolocation) { toast('Geolocation unavailable', 'error'); return; }
    navigator.geolocation.getCurrentPosition(function(p){
      var el = $('#localNearList');
      el.innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
      api.nearbyCompanies(p.coords.latitude, p.coords.longitude, 25).then(function(res){
        var list = res.data || [];
        if (list.length) {
          el.innerHTML = list.slice(0,8).map(function(c){
            var logo = c.logo ? '<img src="' + esc(c.logo) + '" alt="">' : esc((c.name||'C').charAt(0));
            return '<div class="flex gap-3" style="padding:10px 0;border-bottom:1px solid var(--border);cursor:pointer" data-goto="#/company/' + esc(c.id) + '">' +
              '<div class="job-logo" style="width:44px;height:44px">' + logo + '</div>' +
              '<div style="flex:1;min-width:0"><div style="font-weight:600">' + esc(c.name) + '</div>' +
              '<div class="small muted ellipsis">' + esc(c.industry||'') + ' | ' + c.distance + ' km away</div></div></div>';
          }).join('');
        } else { el.innerHTML = '<div class="small muted">No companies found nearby.</div>'; }
      }).catch(function(e){ el.innerHTML = '<div class="small muted">' + esc(e.message||'Failed') + '</div>'; });
    }, function(){ toast('Location denied', 'warn'); });
  };
}

export { renderCompanies, loadCompanies, companyCard, renderCompaniesNear, renderCompany, locBlock, openCompanyForm, openEditCompanyForm, openLocationForm, openLocationPhotoUpload, renderLocal };
