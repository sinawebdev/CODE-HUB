// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { shell, svgIcon } from './layout.js';
import { $, closeAllModals, esc, fmtDate, openModal, toast } from './core.js';

function renderEvents(){
  shell('events', { wide:true, noRail:true });
  $('#main').innerHTML =
    '<div class="flex-between mb-4" style="flex-wrap:wrap;gap:12px">' +
      '<div><h1>Events</h1><p class="muted">Discover career fairs, workshops and networking events.</p></div>' +
      '<div class="flex gap-2"><button class="btn btn-secondary btn-sm" id="myEventsBtn">My events</button>' +
        '<button class="btn btn-primary btn-sm" id="newEventBtn">+ Create event</button></div>' +
    '</div>' +
    '<div id="eventsList"><div class="center-loader"><span class="spinner dark"></span></div></div>';
  $('#newEventBtn').onclick = openEventForm;
  $('#myEventsBtn').onclick = function(){
    var el = $('#eventsList');
    el.innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
    api.myEvents().then(function(res){
      var list = res.data || [];
      el.innerHTML = list.length ? list.map(eventCard).join('') : '<div class="empty"><p>You have not registered for any events yet.</p></div>';
    }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
  };
  loadEvents();
}

function loadEvents(){
  var el = $('#eventsList'); if (!el) return;
  api.getEvents({}).then(function(res){
    var list = res.data || [];
    el.innerHTML = list.length ? list.map(eventCard).join('') : '<div class="empty"><div class="empty-icon">' + svgIcon('calendar') + '</div><h3>No events yet</h3><p>Be the first to create one.</p></div>';
  }).catch(function(e){ el.innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

function eventCard(e){
  return '<div class="card card-pad mb-3">' +
    '<div class="flex-between" style="flex-wrap:wrap;gap:10px">' +
      '<div style="flex:1;min-width:0">' +
        '<h3>' + esc(e.title) + '</h3>' +
        '<div class="flex gap-3 small muted mt-2" style="flex-wrap:wrap">' +
          '<span>' + esc(fmtDate(e.eventDate)) + '</span>' +
          (e.startTime ? '<span>' + esc(e.startTime) + (e.endTime ? '-' + esc(e.endTime) : '') + '</span>' : '') +
          (e.city ? '<span>' + esc(e.city) + '</span>' : '') +
          '<span>' + e.attendeeCount + ' attending</span>' +
        '</div>' +
      '</div>' +
    '</div>' +
    (e.description ? '<p class="muted mt-3 clamp-3">' + esc(e.description) + '</p>' : '') +
    '<div class="flex gap-2 mt-3" style="flex-wrap:wrap">' +
      '<button class="btn btn-primary btn-sm" data-attend="' + esc(e.id) + '">Attend</button>' +
      '<button class="btn btn-secondary btn-sm" data-maybe="' + esc(e.id) + '">Maybe</button>' +
      '<a class="btn btn-ghost btn-sm" target="_blank" href="' + esc(e.mapsLink) + '">View location</a>' +
    '</div>' +
  '</div>';
}

document.addEventListener('click', function(e){
  var a = e.target.closest('[data-attend]');
  if (a) { api.eventAttendance(a.getAttribute('data-attend'), 'Attending').then(function(){ toast('You are attending'); loadEvents(); }).catch(function(err){ toast(err.message||'Failed', 'error'); }); return; }
  var m = e.target.closest('[data-maybe]');
  if (m) { api.eventAttendance(m.getAttribute('data-maybe'), 'Maybe').then(function(){ toast('Marked as maybe'); loadEvents(); }).catch(function(err){ toast(err.message||'Failed', 'error'); }); }
});

function openEventForm(){
  openModal({
    title:'Create event', size:'lg',
    body:'<div class="field"><label>Event title *</label><input class="input" id="evTitle"></div>' +
      '<div class="field"><label>Description</label><textarea class="textarea" id="evDesc" rows="4"></textarea></div>' +
      '<div class="row"><div class="field"><label>Date *</label><input class="input" type="date" id="evDate"></div>' +
        '<div class="field"><label>Max attendees</label><input class="input" type="number" id="evMax" placeholder="0 = unlimited"></div></div>' +
      '<div class="row"><div class="field"><label>Start time</label><input class="input" id="evStart" placeholder="09:00"></div>' +
        '<div class="field"><label>End time</label><input class="input" id="evEnd" placeholder="16:00"></div></div>' +
      '<div class="field"><label>Location name</label><input class="input" id="evLocName"></div>' +
      '<div class="field"><label>Address</label><input class="input" id="evAddr"></div>' +
      '<div class="row"><div class="field"><label>City</label><input class="input" id="evCity" value="Koforidua"></div>' +
        '<div class="field"><label>Region</label><input class="input" id="evRegion" value="Eastern Region"></div></div>' +
      '<label class="flex gap-2 small" style="cursor:pointer"><input type="checkbox" id="evReg" checked> Require registration</label>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="evSubmit">Create event</button>'
  });
  $('#evSubmit').onclick = function(){
    var payload = {
      title: $('#evTitle').value.trim(), description: $('#evDesc').value.trim(),
      eventDate: $('#evDate').value, startTime: $('#evStart').value.trim(),
      endTime: $('#evEnd').value.trim(), locationName: $('#evLocName').value.trim(),
      address: $('#evAddr').value.trim(), city: $('#evCity').value.trim(),
      region: $('#evRegion').value.trim(), maxAttendees: Number($('#evMax').value || 0),
      registrationRequired: $('#evReg').checked
    };
    if (!payload.title) { toast('Title required', 'error'); return; }
    if (!payload.eventDate) { toast('Date required', 'error'); return; }
    var btn = $('#evSubmit'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    api.createEvent(payload).then(function(){ closeAllModals(); toast('Event created'); loadEvents(); })
      .catch(function(e){ toast(e.message||'Failed', 'error'); btn.disabled = false; btn.textContent = 'Create event'; });
  };
}

export { renderEvents, loadEvents, eventCard, openEventForm };
