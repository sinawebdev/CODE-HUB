// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { $, $$, State, avatar, closeAllModals, esc, initials, openModal, timeAgo, toast, verifiedBadge } from './core.js';
import { loadRail, shell } from './layout.js';
import { loadFeed, openComposer } from './feed.js';

function renderHome(){
  if (!State.user) { location.hash = '#/login'; return; }
  if (!State.emailVerified) { location.hash = '#/verify-email'; return; }
  shell('home');
  $('#main').innerHTML =
    '<div class="stories-bar" id="storiesBar">' +
      '<div class="stories-scroll" id="storiesScroll">' +
        '<div class="center-loader" style="padding:8px 0"><span class="spinner dark"></span></div>' +
      '</div>' +
    '</div>' +
    '<div class="card card-pad mb-4" style="cursor:pointer" id="composeTrigger">' +
      '<div class="flex gap-3">' +
        avatar(State.profilePhoto, State.user.FirstName+' '+State.user.LastName, '48') +
        '<div style="flex:1">' +
          '<input class="input" placeholder="Share an update, idea or opportunity..." readonly style="cursor:pointer;background:var(--surface-2)">' +
        '</div>' +
      '</div>' +
      '<div class="flex gap-2 mt-3" style="flex-wrap:wrap">' +
        '<button class="btn btn-ghost btn-sm" data-new-post>Photo / Video</button>' +
        '<button class="btn btn-ghost btn-sm" data-new-story>Story</button>' +
        '<button class="btn btn-ghost btn-sm" data-goto="#/jobs">Job</button>' +
        '<button class="btn btn-ghost btn-sm" data-goto="#/events">Event</button>' +
      '</div>' +
    '</div>' +
    '<div id="feed"><div class="card card-pad mb-4"><div class="flex gap-3"><div class="skeleton sk-avatar"></div><div style="flex:1"><div class="skeleton sk-line" style="width:40%"></div><div class="skeleton sk-line" style="width:80%"></div><div class="skeleton sk-line" style="width:60%"></div></div></div></div></div>';
  $('#composeTrigger').onclick = function(e){ if(e.target.closest('button,a'))return; openComposer(); };
  var ns = $('[data-new-story]', $('#main')); if (ns) ns.onclick = function(e){ e.stopPropagation(); openStoryCreator(); };
  loadRail();
  loadStories();
  loadFeed(true);
}

function loadStories(){
  var el = $('#storiesScroll'); if (!el) return;
  api.getStories().then(function(res){
    State.stories = res.data || [];
    renderStoriesBar();
  }).catch(function(){
    if (el) el.innerHTML = '<div class="small muted" style="padding:8px 10px">Stories unavailable.</div>';
  });
}

function renderStoriesBar(){
  var el = $('#storiesScroll'); if (!el) return;
  var html = '';
  // "Add story" button (only if I don't have one and I'm the first)
  var mine = State.stories.filter(function(g){ return g.isMine; })[0];
  if (!mine) {
    html += '<button class="story-item" data-add-story>' +
      '<div class="story-ring add">' +
        '<div class="story-ring-inner">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
        '</div>' +
      '</div>' +
      '<div class="story-item-name">Add story</div>' +
    '</button>';
  }
  if (!State.stories.length) {
    html += '<div class="small muted" style="align-self:center;padding:0 10px;white-space:nowrap">No stories yet — be the first to share one.</div>';
  }
  State.stories.forEach(function(g, i){
    var ringCls = g.hasUnviewed ? '' : 'viewed';
    var inner = g.user.photo
      ? '<img src="' + esc(g.user.photo) + '" alt="">'
      : '<span style="font-weight:700;color:var(--text-3)">' + esc(initials(g.user.name)) + '</span>';
    html += '<button class="story-item" data-story-group="' + i + '">' +
      '<div class="story-ring ' + ringCls + '">' +
        '<div class="story-ring-inner">' + inner + '</div>' +
      '</div>' +
      '<div class="story-item-name">' + (g.isMine ? 'Your story' : esc(g.user.name.split(' ')[0])) + '</div>' +
    '</button>';
  });
  el.innerHTML = html;
  $$('[data-story-group]', el).forEach(function(b){
    b.onclick = function(){
      var i = parseInt(b.getAttribute('data-story-group'), 10);
      openStoryViewer(i, 0);
    };
  });
  var add = $('[data-add-story]', el); if (add) add.onclick = openStoryCreator;
}

function openStoryCreator(){
  openModal({
    title:'Create story', size:'sm',
    body:
      '<div class="field"><label>Story photo or video</label>' +
        '<input type="file" id="storyFile" accept="image/*,video/mp4" class="input">' +
        '<div class="field-hint">Recommended: square or portrait. Max 8 MB.</div>' +
      '</div>' +
      '<div class="field"><label>Caption (optional)</label>' +
        '<input class="input" id="storyCaption" maxlength="300" placeholder="Add a caption...">' +
      '</div>' +
      '<div id="storyPreview" class="mt-3"></div>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="publishStory" disabled>Share story</button>'
  });
  var fileId = '', fileUrl = '', fileType = '';
  $('#storyFile').onchange = function(ev){
    var f = ev.target.files[0]; if (!f) return;
    if (f.size > 8*1024*1024) { toast('File too large (max 8MB)', 'error'); return; }
    fileType = f.type.indexOf('video') === 0 ? 'video' : 'image';
    toast('Uploading story...', 'warn');
    api.uploadFile('Stories', f).then(function(res){
      fileId = res.data.fileId;
      fileUrl = res.data.url;
      var pv = $('#storyPreview');
      pv.innerHTML = (fileType === 'video'
        ? '<video src="' + esc(fileUrl) + '" controls style="width:100%;border-radius:10px"></video>'
        : '<img src="' + esc(fileUrl) + '" style="width:100%;border-radius:10px;max-height:320px;object-fit:cover">');
      $('#publishStory').disabled = false;
    }).catch(function(e){ toast(e.message || 'Upload failed', 'error'); });
  };
  $('#publishStory').onclick = function(){
    if (!fileId) return;
    var b = this; b.disabled = true; b.innerHTML = '<span class="spinner"></span>';
    api.createStory({
      fileId: fileId, url: fileUrl, type: fileType, caption: $('#storyCaption').value.trim()
    }).then(function(){
      closeAllModals();
      toast('Story shared!');
      loadStories();
    }).catch(function(e){
      toast(e.message || 'Failed', 'error');
      b.disabled = false; b.textContent = 'Share story';
    });
  };
}

function openStoryViewer(groupIndex, storyIndex){
  var group = State.stories[groupIndex]; if (!group) return;
  State.storyGroup = group;
  State.storyIndex = storyIndex;
  State.storyElapsed = 0;
  renderStoryViewer();
}

function renderStoryViewer(){
  var group = State.storyGroup; if (!group) return;
  var story = group.stories[State.storyIndex]; if (!story) return closeStoryViewer();

  var root = $('#storyRoot');
  var dur = story.type === 'video' ? 8000 : 5000;
  var progressSegs = group.stories.map(function(_, i){
    return '<div class="seg">' +
      '<div class="seg-fill" style="width:' + (i < State.storyIndex ? '100%' : '0%') + '"></div>' +
    '</div>';
  }).join('');

  root.innerHTML =
    '<div class="story-viewer" id="storyViewer">' +
      '<div class="story-viewer-inner">' +
        '<div class="story-progress" id="storyProgress">' + progressSegs + '</div>' +
        '<div class="story-head">' +
          avatar(group.user.photo, group.user.name, '40') +
          '<div style="flex:1;min-width:0">' +
            '<div class="story-head-name ellipsis">' + esc(group.user.name) + (group.user.verified ? ' ' + verifiedBadge() : '') + '</div>' +
            '<div class="story-head-time">' + esc(timeAgo(story.createdAt)) + '</div>' +
          '</div>' +
          (story.isMine ? '<button class="story-close" id="storyDelete" title="Delete" style="right:56px">' +
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14"/></svg>' +
          '</button>' : '') +
          '<button class="story-close" id="storyClose" title="Close">' +
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>' +
          '</button>' +
        '</div>' +
        '<div class="story-media">' +
          (story.type === 'video'
            ? '<video id="storyVideo" src="' + esc(story.url) + '" autoplay playsinline></video>'
            : '<img src="' + esc(story.url) + '" alt="">') +
          (story.caption ? '<div class="story-caption">' + esc(story.caption) + '</div>' : '') +
        '</div>' +
        '<button class="story-tap-left" id="storyPrev"></button>' +
        '<button class="story-tap-right" id="storyNext"></button>' +
        '<div class="story-foot">' +
          '<input id="storyReply" placeholder="Send a message...">' +
          '<button id="storySendReply" title="Send">' +
            '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/></svg>' +
          '</button>' +
        '</div>' +
      '</div>' +
    '</div>';

  // Mark viewed
  if (!story.isMine) {
    api.viewStory(story.id).catch(function(){});
  }

  // Progress bar animation
  var fill = $$('#storyProgress .seg-fill')[State.storyIndex];
  var startTime = Date.now();
  function tick(){
    if (!document.body.contains(fill)) return;
    var elapsed = Date.now() - startTime;
    var pct = Math.min(100, (elapsed / dur) * 100);
    fill.style.width = pct + '%';
    if (pct >= 100) {
      storyNext();
    } else {
      State.storyTimer = requestAnimationFrame(tick);
    }
  }
  cancelAnimationFrame(State.storyTimer);
  State.storyTimer = requestAnimationFrame(tick);

  function storyNext(){
    cancelAnimationFrame(State.storyTimer);
    if (State.storyIndex + 1 < State.storyGroup.stories.length) {
      State.storyIndex++;
      renderStoryViewer();
    } else {
      // Move to next group
      var idx = State.stories.indexOf(State.storyGroup);
      if (idx + 1 < State.stories.length) {
        State.storyGroup = State.stories[idx+1];
        State.storyIndex = 0;
        renderStoryViewer();
      } else {
        closeStoryViewer();
      }
    }
  }
  function storyPrev(){
    cancelAnimationFrame(State.storyTimer);
    if (State.storyIndex > 0) { State.storyIndex--; renderStoryViewer(); }
    else {
      var idx = State.stories.indexOf(State.storyGroup);
      if (idx > 0) { State.storyGroup = State.stories[idx-1]; State.storyIndex = State.storyGroup.stories.length - 1; renderStoryViewer(); }
    }
  }

  $('#storyClose').onclick = closeStoryViewer;
  $('#storyNext').onclick = storyNext;
  $('#storyPrev').onclick = storyPrev;
  var del = $('#storyDelete');
  if (del) del.onclick = function(){
    if (!confirm('Delete this story?')) return;
    api.deleteStory(story.id).then(function(){
      toast('Story deleted');
      cancelAnimationFrame(State.storyTimer);
      closeStoryViewer();
      loadStories();
    }).catch(function(e){ toast(e.message||'Failed','error'); });
  };
  var reply = $('#storyReply');
  if (reply) {
    $('#storySendReply').onclick = function(){
      var txt = reply.value.trim(); if (!txt) return;
      reply.value = '';
      api.startConversation(group.userId, '').then(function(r){
        return api.sendMessage(r.data.conversationId, txt, {});
      }).then(function(){
        toast('Reply sent');
      }).catch(function(e){ toast(e.message||'Failed','error'); });
    };
    reply.addEventListener('keydown', function(e){
      if (e.key === 'Enter') { e.preventDefault(); $('#storySendReply').click(); }
    });
  }
}

function closeStoryViewer(){
  cancelAnimationFrame(State.storyTimer);
  var root = $('#storyRoot');
  if (root) root.innerHTML = '';
  State.storyGroup = null;
  State.storyIndex = 0;
}

export { renderHome, loadStories, renderStoriesBar, openStoryCreator, openStoryViewer, renderStoryViewer, closeStoryViewer };
