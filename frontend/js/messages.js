// Ported from the original KoforLink demo; HTTP transport is in api.js.
import * as api from './api.js';
import { refreshCounts, shell, svgIcon } from './layout.js';
import { $, State, avatar, closeAllModals, debounce, esc, openModal, timeAgo, toast } from './core.js';

function renderMessages(conversationId){
  shell('messages', { wide:true, noRail:true });
  $('#main').innerHTML =
    '<header class="page-introduction"><h1>Messages</h1><p>Good conversations start with a connection.</p></header>' +
    '<div class="chat-layout">' +
      '<div class="chat-list" id="chatList">' +
        '<div class="chat-list-head"><div class="flex-between"><h3 style="font-size:15px">Messages</h3>' +
          '<button class="icon-btn" id="newChatBtn" aria-label="Start a conversation" style="width:32px;height:32px">' + svgIcon('plus') + '</button></div></div>' +
        '<div id="chatListItems"><div class="center-loader"><span class="spinner dark"></span></div></div>' +
      '</div>' +
      '<div class="chat-panel" id="chatPanel">' +
        '<div class="empty" style="margin:auto"><div class="empty-icon">' + svgIcon('message') + '</div><h3>Your messages</h3><p>Select a conversation or start a new one.</p></div>' +
      '</div>' +
    '</div>';
  $('#newChatBtn').onclick = openNewChatModal;
  loadConversations();
  if (conversationId) {
    if (conversationId.indexOf('USR-') === 0) {
      api.startConversation(conversationId, '').then(function(res){ openConversation(res.data.conversationId); }).catch(function(){});
    } else { openConversation(conversationId); }
  }
  if (State.chatPoll) clearInterval(State.chatPoll);
  State.chatPoll = setInterval(function(){
    if (State.currentChat && location.hash.indexOf('#/messages')===0) pollMessages();
  }, 6000);
}

function loadConversations(){
  var el = $('#chatListItems'); if (!el) return;
  api.getConversations().then(function(res){
    var list = res.data || [];
    if (!list.length) { el.innerHTML = '<div class="empty" style="padding:40px 20px"><p class="small muted">No conversations yet.</p></div>'; return; }
    el.innerHTML = list.map(function(c){
      return '<div class="chat-item ' + (State.currentChat===c.id?'active':'') + ' ' + (c.unread?'unread':'') + '" data-conv="' + esc(c.id) + '">' +
        avatar(c.avatar, c.title, '48') +
        '<div class="chat-item-body">' +
          '<div class="chat-item-name"><span class="ellipsis">' + esc(c.title) + '</span><span class="chat-item-time">' + (c.lastMessage ? timeAgo(c.lastMessage.createdAt) : '') + '</span></div>' +
          '<div class="chat-item-preview ellipsis">' + (c.lastMessage ? esc((c.lastMessage.senderId===State.user.UserID?'You: ':'') + (c.lastMessage.body||'')) : 'No messages yet') + '</div>' +
        '</div>' +
        (c.unread ? '<span class="chat-unread">' + c.unread + '</span>' : '') +
      '</div>';
    }).join('');
    el.querySelectorAll('[data-conv]').forEach(function(x){ x.onclick = function(){ openConversation(x.getAttribute('data-conv')); }; });
  }).catch(function(e){ el.innerHTML = '<div class="empty" style="padding:20px"><p class="small">' + esc(e.message||'Failed') + '</p></div>'; });
}

function openConversation(convId){
  State.currentChat = convId;
  var panel = $('#chatPanel'); if (!panel) return;
  panel.innerHTML = '<div class="center-loader"><span class="spinner dark"></span></div>';
  api.getMessages(convId, '').then(function(res){
    var messages = res.data.messages, conversation = res.data.conversation;
    panel.innerHTML =
      '<div class="chat-head">' + avatar(conversation.avatar, conversation.title, '40') +
        '<div style="flex:1;min-width:0"><div style="font-weight:600" class="ellipsis">' + esc(conversation.title) + '</div>' +
        '<div class="small muted">' + (conversation.memberCount>2 ? esc(conversation.memberCount + ' members') : 'Direct message') + '</div></div>' +
        '<button class="icon-btn" id="chatSearchBtn" title="Search messages"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg></button>' +
        '<button class="icon-btn" id="chatPinBtn" title="' + (conversation.pinned?'Unpin':'Pin') + '">' +
          '<svg viewBox="0 0 24 24" fill="' + (conversation.pinned?'currentColor':'none') + '" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 17v5M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z"/></svg>' +
        '</button>' +
      '</div>' +
      '<div class="chat-scroll" id="chatScroll">' + (messages.length ? messages.map(msgBlock).join('') : '<div class="empty" style="padding:40px"><p class="small muted">No messages yet. Say hello!</p></div>') + '</div>' +
      '<div class="chat-input"><textarea class="textarea" id="chatInput" rows="1" placeholder="Write a message..."></textarea>' +
        '<button class="btn btn-primary btn-icon" id="chatSendBtn"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/></svg></button></div>';
    var scroll = $('#chatScroll'); if (scroll) scroll.scrollTop = scroll.scrollHeight;
    loadConversations();
    $('#chatSendBtn').onclick = function(){ sendChatMessage(convId); };
    $('#chatInput').onkeydown = function(e){ if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(convId); } };
    $('#chatPinBtn').onclick = function(){
      api.setConversationFlag(convId, 'pinned', !conversation.pinned).then(function(){
        toast(conversation.pinned ? 'Unpinned' : 'Pinned'); openConversation(convId);
      }).catch(function(e){ toast(e.message||'Failed', 'error'); });
    };
    $('#chatSearchBtn').onclick = function(){
      openModal({ title:'Search in conversation', size:'sm',
        body:'<input class="input" id="msgSearch" placeholder="Search messages..."><div id="msgSearchResults" class="mt-3"></div>' });
      var inp = $('#msgSearch'); inp.focus();
      inp.addEventListener('input', debounce(function(){
        var q = inp.value.trim();
        if (q.length < 2) { $('#msgSearchResults').innerHTML = ''; return; }
        api.searchMessages(convId, q).then(function(r){
          $('#msgSearchResults').innerHTML = (r.data||[]).map(function(m){
            return '<div class="comment" style="padding:8px 0;border-bottom:1px solid var(--border)"><div class="comment-body"><div class="comment-text">' + esc(m.body) + '</div><div class="small muted mt-2">' + esc(m.timeAgo) + '</div></div></div>';
          }).join('') || '<p class="small muted">No matches.</p>';
        }).catch(function(){});
      }, 350));
    };
    refreshCounts();
  }).catch(function(e){ panel.innerHTML = '<div class="empty" style="margin:auto"><p>' + esc(e.message||'Failed') + '</p></div>'; });
}

function msgBlock(m){
  return '<div class="msg ' + (m.mine?'mine':'theirs') + '" data-msg="' + esc(m.id) + '">' +
    (!m.mine ? '<div class="small" style="font-weight:600;font-size:11px;opacity:.75;margin-bottom:2px">' + esc(m.senderName) + '</div>' : '') +
    (m.deleted ? '<em class="muted">Message deleted</em>' : esc(m.body)) +
    (m.attachmentUrl ? '<div class="msg-attachment">' + (m.attachmentType==='video'
      ? '<video src="' + esc(m.attachmentUrl) + '" controls style="max-width:100%"></video>'
      : '<a href="' + esc(m.attachmentUrl) + '" target="_blank"><img src="' + esc(m.attachmentUrl) + '" alt=""></a>') + '</div>' : '') +
    '<span class="msg-time">' + esc(m.timeAgo) + (m.mine?' sent':'') + '</span>' +
  '</div>';
}

function sendChatMessage(convId){
  var input = $('#chatInput'); if (!input) return;
  var body = input.value.trim(); if (!body) return;
  input.value = '';
  api.sendMessage(convId, body, {}).then(function(res){
    var scroll = $('#chatScroll');
    if (scroll) {
      var empty = scroll.querySelector('.empty'); if (empty) empty.remove();
      if (!Array.from(scroll.querySelectorAll('[data-msg]')).some(function(el){return el.dataset.msg === res.data.id;})) scroll.insertAdjacentHTML('beforeend', msgBlock(res.data));
      scroll.scrollTop = scroll.scrollHeight;
    }
    loadConversations();
  }).catch(function(e){ toast(e.message||'Failed', 'error'); input.value = body; });
}

function pollMessages(){
  var convId = State.currentChat; if (!convId) return;
  var scroll = $('#chatScroll'); if (!scroll) return;
  var lastMsg = scroll.lastElementChild;
  var lastId = lastMsg && lastMsg.getAttribute('data-msg');
  api.getMessages(convId, lastId || '').then(function(res){
    var messages = res.data.messages || [];
    if(State.currentChat !== convId || scroll !== $('#chatScroll'))return;
    var existing=new Set(Array.from(scroll.querySelectorAll('[data-msg]')).map(function(el){return el.dataset.msg;}));
    var fresh=messages.filter(function(m){if(existing.has(m.id))return false;existing.add(m.id);return true;});
    if (fresh.length) { var empty=scroll.querySelector('.empty');if(empty)empty.remove();fresh.forEach(function(m){ scroll.insertAdjacentHTML('beforeend', msgBlock(m)); }); scroll.scrollTop = scroll.scrollHeight; }
  }).catch(function(){});
}

function openNewChatModal(){
  api.getConnections('').then(function(res){
    var list = res.data || [];
    openModal({
      title:'New message',
      body:'<input class="input mb-3" id="newChatSearch" placeholder="Search connections...">' +
        '<div id="newChatList" style="max-height:400px;overflow-y:auto">' +
          (list.map(function(c){
            return '<div class="flex gap-3" style="padding:10px 0;border-bottom:1px solid var(--border);cursor:pointer" data-new-chat="' + esc(c.userId) + '">' +
              avatar(c.photo, c.name, '40') +
              '<div style="flex:1;min-width:0"><div style="font-weight:600">' + esc(c.name) + '</div><div class="small muted ellipsis">' + esc(c.headline||'') + '</div></div></div>';
          }).join('') || '<p class="small muted">No connections yet.</p>') +
        '</div>',
      footer:'<button class="btn btn-ghost" data-close>Cancel</button>'
    });
    $('#newChatList').querySelectorAll('[data-new-chat]').forEach(function(x){ x.onclick = function(){
      api.startConversation(x.getAttribute('data-new-chat'), '').then(function(r){
        closeAllModals(); location.hash = '#/messages';
        setTimeout(function(){ openConversation(r.data.conversationId); }, 100);
      }).catch(function(e){ toast(e.message||'Failed', 'error'); });
    }; });
    var search = $('#newChatSearch');
    search.addEventListener('input', debounce(function(){
      var q = search.value.toLowerCase();
      $('#newChatList').querySelectorAll('[data-new-chat]').forEach(function(el){
        el.style.display = el.textContent.toLowerCase().indexOf(q) !== -1 ? '' : 'none';
      });
    }, 200));
  }).catch(function(e){ toast(e.message||'Failed', 'error'); });
}

export { renderMessages, loadConversations, openConversation, msgBlock, sendChatMessage, pollMessages, openNewChatModal };
