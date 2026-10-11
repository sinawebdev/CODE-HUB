import { animateFeedback } from './motion.js';

const icons = {
  success:'<polyline points="20 6 9 17 4 12"/>',
  error:'<circle cx="12" cy="12" r="9"/><path d="M12 8v4M12 16h.01"/>',
  warn:'<path d="M12 3 2 20h20L12 3Z"/><path d="M12 9v4M12 17h.01"/>'
};

function feedbackIcon(type){
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (icons[type] || icons.success) + '</svg>';
}

function toast(message, type){
  type = icons[type] ? type : 'success';
  const root = document.getElementById('toasts');
  if (!root) return;
  const existing = Array.from(root.children).find(function(item){ return item.dataset.message === message && item.dataset.type === type; });
  if (existing) { existing._restart(); return; }
  const card = document.createElement('div');
  card.className = 'toast ' + type;
  card.dataset.message = message;
  card.dataset.type = type;
  card.setAttribute('role', type === 'error' ? 'alert' : 'status');
  card.setAttribute('aria-atomic', 'true');
  card.innerHTML = '<span class="feedback-icon">' + feedbackIcon(type) + '</span><div class="feedback-copy"><strong></strong><p></p></div><button type="button" class="feedback-dismiss" aria-label="Dismiss notification">' +
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6"/></svg></button>';
  card.querySelector('strong').textContent = type === 'error' ? 'Something needs attention' : type === 'warn' ? 'Please note' : 'All set';
  card.querySelector('p').textContent = message;
  let timer;
  const dismiss = function(){ clearTimeout(timer); card.remove(); };
  const pause = function(){ clearTimeout(timer); };
  const restart = function(){
    pause();
    // Errors remain until dismissed; other feedback pauses while being read.
    if (type !== 'error' && !card.matches(':hover') && !card.contains(document.activeElement)) timer = setTimeout(dismiss, 6500);
  };
  card._restart = restart;
  card.querySelector('button').onclick = dismiss;
  card.addEventListener('mouseenter', pause);
  card.addEventListener('mouseleave', restart);
  card.addEventListener('focusin', pause);
  card.addEventListener('focusout', function(){ requestAnimationFrame(restart); });
  // Keep persistent errors available. Limit only old transient notifications.
  const transient = Array.from(root.children).filter(function(item){ return item.dataset.type !== 'error'; });
  if (transient.length >= 2) transient[0].querySelector('button').click();
  root.appendChild(card);
  animateFeedback(card);
  restart();
}

export { toast, feedbackIcon };
