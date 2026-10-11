// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { $, $$, State, avatar, closeAllModals, confirmAction, copyLink, esc, openModal, timeAgo, toast, verifiedBadge } from './core.js';
import { animateAction } from './motion.js';
import { shell, svgIcon } from './layout.js';

function loadFeed(reset){
  if (reset) State.feed = { posts: [], offset: 0, hasMore: true, loading: false };
  if (State.feed.loading || !State.feed.hasMore) return;
  State.feed.loading = true;
  var feedEl = $('#feed'); if (feedEl) feedEl.setAttribute('aria-busy','true');
  var loadMore = $('#loadMore'); if (loadMore) { loadMore.disabled = true; loadMore.textContent = 'Loading updates...'; }
  api.getFeed({ offset: State.feed.offset, limit: 20 }).then(function(res){
    var posts = res.data.posts, hasMore = res.data.hasMore;
    State.feed.posts = State.feed.posts.concat(posts);
    State.feed.hasMore = hasMore;
    State.feed.offset += posts.length;
    renderFeedPosts();
  }).catch(function(e){
    toast(e.message || 'Failed to load feed', 'error');
    if (!State.feed.posts.length && $('#feed')) {
      $('#feed').innerHTML = '<div class="empty"><h3>Updates could not load</h3><p>Please try again to see what your network has shared.</p><button class="btn btn-secondary mt-4" id="feedRetry">Try again</button></div>';
      $('#feedRetry').onclick = function(){ loadFeed(true); };
    }
    if (loadMore) { loadMore.disabled = false; loadMore.textContent = 'Load more posts'; }
  }).then(function(){
    State.feed.loading = false;
    if ($('#feed')) $('#feed').setAttribute('aria-busy','false');
  });
}

function renderFeedPosts(){
  var el = $('#feed'); if (!el) return;
  if (!State.feed.posts.length) {
    el.innerHTML = '<div class="empty"><div class="empty-icon">' + svgIcon('network') + '</div><h3>Make your first connection</h3><p>Connect with people and follow companies. Their updates will bring this space to life.</p><button class="btn btn-primary mt-4" data-goto="#/network">Find your people</button></div>';
    return;
  }
  el.innerHTML = State.feed.posts.map(postCard).join('') + (State.feed.hasMore
    ? '<button class="btn btn-secondary btn-block mt-4" id="loadMore">Load more posts</button>' : '');
  var lm = $('#loadMore'); if (lm) lm.onclick = function(){ loadFeed(false); };
  bindCarousels();
}

function postCard(p){
  if (!p) return '';
  var author = p.author || {};
  var mediaHtml = '';
  if (p.media && p.media.length) {
    if (p.media.length === 1) {
      var m = p.media[0];
      mediaHtml = '<div class="post-media">' + (m.type==='video'
        ? '<video src="' + esc(m.url) + '" controls playsinline></video>'
        : '<img src="' + esc(m.url) + '" alt="' + esc(m.caption || 'Photo shared by ' + (author.name || 'a community member')) + '" loading="lazy">') + '</div>';
    } else {
      var slides = p.media.map(function(m){
        return '<div class="slide">' + (m.type==='video'
          ? '<video src="' + esc(m.url) + '" controls playsinline></video>'
          : '<img src="' + esc(m.url) + '" alt="' + esc(m.caption || 'Photo shared by ' + (author.name || 'a community member')) + '" loading="lazy">') + '</div>';
      }).join('');
      var dots = p.media.map(function(_,i){
        return '<span class="' + (i===0?'active':'') + '"></span>';
      }).join('');
      mediaHtml = '<div class="post-media" style="background:transparent">' +
        '<div class="post-carousel" data-carousel="' + esc(p.id) + '" data-count="' + p.media.length + '">' + slides + '</div>' +
        '<button class="carousel-nav prev" data-car-prev="' + esc(p.id) + '" aria-label="Previous">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg></button>' +
        '<button class="carousel-nav next" data-car-next="' + esc(p.id) + '" aria-label="Next">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg></button>' +
        '<div class="carousel-dots" data-car-dots="' + esc(p.id) + '">' + dots + '</div>' +
      '</div>';
    }
  }
  return '<article class="post" data-post-id="' + esc(p.id) + '">' +
    '<div class="post-head">' +
      '<a href="#/user/' + esc(author.userId) + '" aria-label="View ' + esc(author.name || 'member') + ' profile">' + avatar(author.photo, author.name, '44') + '</a>' +
      '<div class="post-author">' +
        '<div class="post-author-name">' +
          '<a href="#/user/' + esc(author.userId) + '" style="color:inherit">' + esc(author.name) + '</a>' +
          (author.verified ? verifiedBadge() : '') +
        '</div>' +
        '<div class="post-author-sub">' + (author.headline ? esc(author.headline) + ' &middot; ' : '') + '<time datetime="' + esc(p.createdAt) + '">' + esc(timeAgo(p.createdAt)) + '</time></div>' +
        (p.company ? '<div class="small" style="color:var(--brand);font-weight:600;margin-top:2px">' + esc(p.company.name) + (p.company.verified ? ' ' + verifiedBadge() : '') + '</div>' : '') +
      '</div>' +
      '<button class="icon-btn" data-post-menu="' + esc(p.id) + '" aria-label="Post options" aria-haspopup="menu" aria-expanded="false">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>' +
      '</button>' +
    '</div>' +
    (p.repostOf ? '<div class="repost-label">' + svgIcon('network') + ' Reposted</div>' : '') +
    (p.content ? '<div class="post-body">' + esc(p.content) + '</div>' : '') +
    mediaHtml +
    (p.repostOf ? '<div class="repost-wrap">' + postCard(p.repostOf) + '</div>' : '') +
    '<div class="post-stats">' +
      (p.likeCount>0 ? '<span>' + p.likeCount + ' like' + (p.likeCount===1?'':'s') + '</span>' : '') +
      (p.commentCount>0 ? '<span>' + p.commentCount + ' comment' + (p.commentCount===1?'':'s') + '</span>' : '') +
      (p.viewCount>0 ? '<span style="margin-left:auto">' + p.viewCount + ' views</span>' : '') +
    '</div>' +
    '<div class="post-actions">' +
      '<button class="post-action ' + (p.liked?'liked':'') + '" data-like="' + esc(p.id) + '" aria-pressed="' + !!p.liked + '">' +
        '<svg viewBox="0 0 24 24" fill="' + (p.liked?'currentColor':'none') + '" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>' +
        '<span>Like</span>' +
      '</button>' +
      '<button class="post-action" data-comment-toggle="' + esc(p.id) + '" aria-expanded="false">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>' +
        '<span>Comment</span>' +
      '</button>' +
      '<button class="post-action" data-share="' + esc(p.id) + '">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>' +
        '<span>Share</span>' +
      '</button>' +
      '<button class="post-action ' + (p.saved?'saved':'') + '" data-save="' + esc(p.id) + '" aria-pressed="' + !!p.saved + '">' +
        '<svg viewBox="0 0 24 24" fill="' + (p.saved?'currentColor':'none') + '" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="m19 21-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>' +
        '<span>Save</span>' +
      '</button>' +
    '</div>' +
    '<div class="post-comments hidden" data-comments="' + esc(p.id) + '"></div>' +
  '</article>';
}

function bindCarousels(){
  $$('.post-carousel').forEach(function(car){
    if (car._bound) return;
    car._bound = true;
    car.addEventListener('scroll', function(){
      var idx = Math.round(car.scrollLeft / car.clientWidth);
      var dots = document.querySelector('[data-car-dots="' + car.getAttribute('data-carousel') + '"]');
      if (dots) $$('span', dots).forEach(function(s, i){ s.classList.toggle('active', i===idx); });
    }, { passive: true });
  });
}

function carouselMotion(event){
  return event.detail === 0 || window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
}

document.addEventListener('click', function(e){
  var prev = e.target.closest('[data-car-prev]');
  if (prev) {
    var id = prev.getAttribute('data-car-prev');
    var car = document.querySelector('[data-carousel="' + id + '"]');
    if (car) car.scrollBy({ left: -car.clientWidth, behavior: carouselMotion(e) });
    return;
  }
  var next = e.target.closest('[data-car-next]');
  if (next) {
    var id2 = next.getAttribute('data-car-next');
    var car2 = document.querySelector('[data-carousel="' + id2 + '"]');
    if (car2) car2.scrollBy({ left: car2.clientWidth, behavior: carouselMotion(e) });
    return;
  }
  var likeBtn = e.target.closest('[data-like]');
  if (likeBtn) {
    e.preventDefault();
    if (likeBtn.disabled) return;
    likeBtn.disabled = true;
    var pid = likeBtn.getAttribute('data-like');
    api.react(pid, 'like').then(function(res){
      var p = null;
      for (var i=0;i<State.feed.posts.length;i++) { if (State.feed.posts[i].id===pid) { p = State.feed.posts[i]; break; } }
      if (p) { p.liked = res.data.liked; p.likeCount = res.data.count; }
      likeBtn.classList.toggle('liked', res.data.liked);
      likeBtn.setAttribute('aria-pressed', String(!!res.data.liked));
      var svg = likeBtn.querySelector('svg'); if (svg) svg.setAttribute('fill', res.data.liked?'currentColor':'none');
      animateAction(likeBtn, res.data.liked);
      var root = document.querySelector('[data-post-id="' + pid + '"]');
      if (root) {
        var stats = root.querySelector('.post-stats');
        if (stats) {
          var likes = res.data.count>0 ? '<span>' + res.data.count + ' like' + (res.data.count===1?'':'s') + '</span>' : '';
          var comments = p && p.commentCount>0 ? '<span>' + p.commentCount + ' comment' + (p.commentCount===1?'':'s') + '</span>' : '';
          var views = p && p.viewCount>0 ? '<span style="margin-left:auto">' + p.viewCount + ' views</span>' : '';
          stats.innerHTML = likes + comments + views;
        }
      }
    }).catch(function(err){ toast(err.message||'Failed', 'error'); }).finally(function(){ likeBtn.disabled = false; });
    return;
  }
  var saveBtn = e.target.closest('[data-save]');
  if (saveBtn) {
    e.preventDefault();
    if (saveBtn.disabled) return;
    saveBtn.disabled = true;
    var sid = saveBtn.getAttribute('data-save');
    var isSaved = saveBtn.classList.contains('saved');
    api.savePost(sid, !isSaved).then(function(res){
      saveBtn.classList.toggle('saved', res.data.saved);
      saveBtn.setAttribute('aria-pressed', String(!!res.data.saved));
      var svg = saveBtn.querySelector('svg'); if (svg) svg.setAttribute('fill', res.data.saved?'currentColor':'none');
      animateAction(saveBtn, res.data.saved);
      for (var i=0;i<State.feed.posts.length;i++) { if (State.feed.posts[i].id===sid) { State.feed.posts[i].saved = res.data.saved; break; } }
      toast(res.data.saved ? 'Post saved' : 'Removed from saved');
    }).catch(function(err){ toast(err.message||'Failed', 'error'); }).finally(function(){ saveBtn.disabled = false; });
    return;
  }
  var shareBtn = e.target.closest('[data-share]');
  if (shareBtn) {
    e.preventDefault();
    var shid = shareBtn.getAttribute('data-share');
    api.sharePost(shid).then(function(){
      var url = location.origin + location.pathname + '#/post/' + shid;
      copyLink(url);
    }).catch(function(err){ toast(err.message||'Failed', 'error'); });
    return;
  }
  var commentToggle = e.target.closest('[data-comment-toggle]');
  if (commentToggle) { e.preventDefault(); toggleComments(commentToggle.getAttribute('data-comment-toggle')); return; }
  var menuBtn = e.target.closest('[data-post-menu]');
  if (menuBtn) { e.preventDefault(); openPostMenu(menuBtn.getAttribute('data-post-menu'), menuBtn); return; }
});

function toggleComments(postId){
  var box = document.querySelector('[data-comments="' + postId + '"]');
  if (!box) return;
  var toggle = document.querySelector('[data-comment-toggle="' + postId + '"]');
  if (!box.classList.contains('hidden')) { box.classList.add('hidden'); if (toggle) toggle.setAttribute('aria-expanded','false'); return; }
  box.classList.remove('hidden');
  if (toggle) toggle.setAttribute('aria-expanded','true');
  box.innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  api.getComments(postId).then(function(res){
    var comments = res.data || [];
    var html = '<div style="padding:8px 16px 12px;border-top:1px solid var(--border)">' +
      '<div id="commentsList-' + esc(postId) + '">';
    if (comments.length) {
      comments.forEach(function(c){ html += commentRow(c, postId); });
    } else {
      html += '<div class="small muted" style="padding:6px 0">No comments yet. Be the first.</div>';
    }
    html += '</div>' +
      '<div class="flex gap-2 mt-3">' +
        avatar(State.profilePhoto, State.user.FirstName, '32') +
        '<input class="input" placeholder="Write a comment..." aria-label="Write a comment" data-comment-input="' + esc(postId) + '">' +
        '<button class="btn btn-primary btn-sm" data-comment-submit="' + esc(postId) + '">Post</button>' +
      '</div>' +
    '</div>';
    box.innerHTML = html;
  }).catch(function(){ box.innerHTML = '<div class="small muted" style="padding:12px 16px">Failed to load comments.</div>'; });
}

function commentRow(c, postId){
  return '<div class="comment" style="padding:8px 0" data-comment-id="' + esc(c.id) + '">' +
    avatar(c.author.photo, c.author.name, '32') +
    '<div class="comment-body">' +
      '<div class="comment-author">' + esc(c.author.name) + (c.author.verified ? ' ' + verifiedBadge() : '') + '</div>' +
      '<div class="comment-text">' + esc(c.content) + '</div>' +
      '<div class="small muted mt-2">' + esc(c.timeAgo) + (c.isMine ? ' · <button class="btn-ghost small" style="color:var(--danger);padding:0" data-del-comment="' + esc(c.id) + '">Delete</button>' : '') + '</div>' +
    '</div>' +
  '</div>';
}

document.addEventListener('click', async function(e){
  var del = e.target.closest('[data-del-comment]');
  if (del) {
    if (!await confirmAction({ title:'Delete this comment?', message:'Your comment will be permanently removed from this conversation.' })) return;
    api.deleteComment(del.getAttribute('data-del-comment')).then(function(){
      var row = del.closest('[data-comment-id]');
      if (row) row.remove();
      toast('Comment deleted');
    }).catch(function(err){ toast(err.message||'Failed','error'); });
  }
});

function submitComment(postId){
  var input = document.querySelector('[data-comment-input="' + postId + '"]');
  if (!input) return;
  var content = input.value.trim();
  if (!content) return;
  input.value = '';
  api.comment(postId, content, '').then(function(res){
    var list = document.querySelector('#commentsList-' + postId);
    if (list) {
      var empty = list.querySelector('.small.muted'); if (empty) empty.remove();
      var c = res.data;
      c.isMine = true;
      list.insertAdjacentHTML('beforeend', commentRow(c, postId));
    }
    for (var i=0;i<State.feed.posts.length;i++) {
      if (State.feed.posts[i].id===postId) { State.feed.posts[i].commentCount = (State.feed.posts[i].commentCount||0)+1; break; }
    }
    toast('Comment added');
  }).catch(function(err){ toast(err.message||'Failed', 'error'); });
}

document.addEventListener('keydown', function(e){
  if (e.key !== 'Enter' || e.shiftKey) return;
  var input = e.target.closest('[data-comment-input]');
  if (!input) return;
  e.preventDefault();
  submitComment(input.getAttribute('data-comment-input'));
});

document.addEventListener('click', function(e){
  var btn = e.target.closest('[data-comment-submit]');
  if (!btn) return;
  submitComment(btn.getAttribute('data-comment-submit'));
});

function openPostMenu(postId, anchor){
  var existing = document.querySelector('.dropdown.post-menu'); if (existing) { if (existing._close) existing._close(); else existing.remove(); }
  var p = null;
  for (var i=0;i<State.feed.posts.length;i++) { if (State.feed.posts[i].id===postId) { p = State.feed.posts[i]; break; } }
  var isMine = p && p.isMine;
  var dd = document.createElement('div');
  dd.className = 'dropdown post-menu';
  dd.setAttribute('role','menu');
  dd.setAttribute('aria-label','Post options');
  anchor.setAttribute('aria-expanded','true');
  dd.innerHTML = '<button class="dropdown-item" data-act="copy">Copy link</button>' +
    (isMine ? '<button class="dropdown-item" data-act="edit">Edit post</button>' +
      '<button class="dropdown-item danger" data-act="delete">Delete post</button>' : '') +
    '<button class="dropdown-item danger" data-act="report">Report</button>';
  document.body.appendChild(dd);
  dd.querySelectorAll('button').forEach(function(button){ button.setAttribute('role','menuitem'); });
  var rect = anchor.getBoundingClientRect();
  dd.style.top = (rect.bottom + window.scrollY + 6) + 'px';
  dd.style.left = Math.max(8, rect.right - 200) + 'px';
  var close = function(){ dd.remove(); anchor.setAttribute('aria-expanded','false'); document.removeEventListener('click', close); };
  dd._close = close;
  dd.querySelector('button').focus();
  dd.addEventListener('keydown', function(e){
    var buttons = Array.from(dd.querySelectorAll('button'));
    var index = buttons.indexOf(document.activeElement);
    if (e.key === 'Escape') { e.preventDefault(); close(); anchor.focus(); }
    else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault(); buttons[(index + (e.key === 'ArrowDown' ? 1 : buttons.length - 1)) % buttons.length].focus();
    } else if (e.key === 'Tab') { anchor.focus(); close(); }
  });
  setTimeout(function(){ if (dd.isConnected) document.addEventListener('click', close, {once:true}); }, 0);
  dd.addEventListener('click', async function(ev){
    var actEl = ev.target.closest('[data-act]');
    var act = actEl ? actEl.getAttribute('data-act') : null;
    if (!act) return;
    close();
    if (act === 'copy') {
      var url = location.origin + location.pathname + '#/post/' + postId;
      copyLink(url);
    } else if (act === 'edit') {
      openModal({
        title:'Edit post',
        body:'<textarea class="textarea" id="editPostContent" rows="6">' + esc(p.content) + '</textarea>',
        footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
          '<button class="btn btn-primary" id="editPostSave">Save</button>'
      });
      $('#editPostSave').onclick = function(){
        var content = $('#editPostContent').value.trim();
        api.updatePost(postId, content).then(function(){
          if (p) p.content = content;
          closeAllModals(); toast('Post updated'); loadFeed(true);
        }).catch(function(e){ toast(e.message||'Failed', 'error'); });
      };
    } else if (act === 'delete') {
      if (!await confirmAction({ title:'Delete this post?', message:'Your post and its conversation will be permanently removed. This cannot be undone.' })) return;
      api.deletePost(postId).then(function(){
        State.feed.posts = State.feed.posts.filter(function(x){ return x.id!==postId; });
        var el = document.querySelector('[data-post-id="' + postId + '"]'); if (el) el.remove();
        toast('Post deleted');
      }).catch(function(e){ toast(e.message||'Failed', 'error'); });
    } else if (act === 'report') { openReportModal('Post', postId); }
  });
}

function openComposer(){
  openModal({
    title:'Create post',
    body:'<div class="flex gap-3 mb-3">' +
        avatar(State.profilePhoto, State.user.FirstName, '40') +
        '<div style="flex:1">' +
          '<div style="font-weight:600">' + esc(State.user.FirstName + ' ' + State.user.LastName) + '</div>' +
          '<div class="small muted">' + esc(State.user.ProfessionalTitle || '') + '</div>' +
        '</div>' +
      '</div>' +
      '<label class="composer-text-label" for="composerText">Share with your network</label><textarea class="textarea" id="composerText" rows="5" placeholder="Share an update, opportunity or idea..."></textarea>' +
      '<div id="composerMedia" class="mt-3"></div>' +
      '<div class="flex gap-2 mt-3" style="flex-wrap:wrap">' +
        '<label class="btn btn-ghost btn-sm" style="cursor:pointer">' +
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>' +
          ' Photo / Video' +
          '<input type="file" id="composerFile" accept="image/*,video/mp4" hidden>' +
        '</label>' +
      '</div>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-primary" id="composerPost">Publish</button>'
  });
  var pendingMedia = [];
  $('#composerFile').onchange = function(ev){
    var file = ev.target.files[0]; if (!file) return;
    if (file.size > 5*1024*1024) { toast('File too large (max 5MB)', 'error'); return; }
    toast('Uploading...', 'warn');
    api.uploadFile('Post Media', file).then(function(res){
      pendingMedia.push({
        fileId: res.data.fileId, url: res.data.url,
        type: file.type.indexOf('video')===0 ? 'video' : 'image',
        caption: ''
      });
      renderComposerMedia();
    }).catch(function(e){ toast(e.message||'Upload failed', 'error'); });
  };
  function renderComposerMedia(){
    var el = $('#composerMedia'); if (!el) return;
    el.innerHTML = pendingMedia.map(function(m,i){
      var thumb = m.type === 'video'
        ? '<video src="' + m.url + '" style="width:100px;height:100px;object-fit:cover;border-radius:8px;border:1px solid var(--border)"></video>'
        : '<img src="' + m.url + '" style="width:100px;height:100px;object-fit:cover;border-radius:8px;border:1px solid var(--border)">';
      return '<div style="position:relative;display:inline-block;margin:4px">' + thumb +
        '<button class="icon-btn" style="position:absolute;top:2px;right:2px;width:24px;height:24px;background:rgba(0,0,0,.6);color:#fff" data-remove-media="' + i + '">×</button>' +
      '</div>';
    }).join('');
    el.querySelectorAll('[data-remove-media]').forEach(function(b){
      b.onclick = function(){ pendingMedia.splice(+b.getAttribute('data-remove-media'),1); renderComposerMedia(); };
    });
  }
  $('#composerPost').onclick = function(){
    var content = $('#composerText').value.trim();
    if (!content && !pendingMedia.length) { toast('Write something or attach media', 'error'); return; }
    var btn = $('#composerPost'); btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    api.createPost({ content: content, media: pendingMedia }).then(function(){
      closeAllModals(); toast('Post published'); loadFeed(true);
    }).catch(function(e){ toast(e.message||'Failed', 'error'); btn.disabled = false; btn.textContent = 'Publish'; });
  };
}

function renderPost(postId){
  shell('home', { wide:true });
  $('#main').innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  api.getPost(postId).then(function(res){
    State.feed.posts = [res.data];
    $('#main').innerHTML = '<button class="btn btn-ghost btn-sm mb-3" data-goto="#/">Back</button>' + postCard(res.data);
    bindCarousels();
    toggleComments(postId);
  }).catch(function(e){ $('#main').innerHTML = '<div class="empty"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

function openReportModal(targetType, targetId){
  openModal({
    title:'Report', size:'sm',
    body:'<div class="field"><label>Reason</label>' +
        '<select class="select" id="repReason"><option>Spam</option><option>Fraud</option><option>Harassment</option><option>Fake account</option><option>Inappropriate content</option><option>Scam</option><option>Other</option></select></div>' +
      '<div class="field"><label>Details (optional)</label><textarea class="textarea" id="repDetails" rows="3"></textarea></div>',
    footer:'<button class="btn btn-ghost" data-close>Cancel</button>' +
      '<button class="btn btn-danger" id="repSubmit">Submit report</button>'
  });
  $('#repSubmit').onclick = function(){
    api.report(targetType, targetId, $('#repReason').value, $('#repDetails').value.trim()).then(function(){
      closeAllModals(); toast('Report submitted. Thank you.');
    }).catch(function(e){ toast(e.message||'Failed', 'error'); });
  };
}

export { loadFeed, renderFeedPosts, postCard, bindCarousels, toggleComments, commentRow, submitComment, openPostMenu, openComposer, renderPost, openReportModal };
