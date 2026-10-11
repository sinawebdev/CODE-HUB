// Short GSAP timelines following HyperFrames' interaction and easing principles.
// The video composition runtime is not needed for live application controls.
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const running = new Set();

function runMotion(build, restore){
  if (reducedMotion.matches || !window.gsap) return;
  let timeline;
  const cleanup = function(){
    if (!running.has(cleanup)) return;
    running.delete(cleanup);
    const finished = timeline;
    timeline = null;
    if (finished) finished.kill();
    restore();
  };
  timeline = window.gsap.timeline({ onComplete:cleanup, onInterrupt:cleanup });
  running.add(cleanup);
  build(timeline);
}

reducedMotion.addEventListener('change', function(event){
  if (event.matches) Array.from(running).forEach(function(cleanup){ cleanup(); });
});

function animateAction(button, active){
  if (!button || !button.isConnected || reducedMotion.matches || !window.gsap) return;
  const target = button.querySelector('svg') || button;
  const particles = [];
  if (active && target !== button) {
    const box = button.getBoundingClientRect(), icon = target.getBoundingClientRect();
    for (let i = 0; i < 4; i++) {
      const dot = document.createElement('span');
      dot.className = 'action-particle';
      dot.setAttribute('aria-hidden', 'true');
      dot.style.left = (icon.left - box.left + icon.width / 2) + 'px';
      dot.style.top = (icon.top - box.top + icon.height / 2) + 'px';
      button.appendChild(dot);
      particles.push(dot);
    }
  }
  runMotion(function(tl){
    tl.fromTo(target, { scale:0.8 }, { scale:active ? 1.2 : 1, duration:0.16, ease:'power2.out', transformOrigin:'50% 50%' })
      .to(target, { scale:1, duration:0.22, ease:'back.out(2)' });
    particles.forEach(function(dot, i){
      const angle = Math.PI * (i / 2 + 0.25);
      tl.fromTo(dot, { scale:0.5, opacity:1 }, { x:Math.cos(angle) * 20, y:Math.sin(angle) * 20, scale:0, opacity:0, duration:0.36, ease:'power2.out' }, 0);
    });
  }, function(){
    window.gsap.set(target, { clearProps:'transform,transformOrigin' });
    particles.forEach(function(dot){ dot.remove(); });
  });
}

function animateFeedback(element){
  runMotion(function(tl){
    tl.fromTo(element, { opacity:0, y:-12 }, { opacity:1, y:0, duration:0.24, ease:'power3.out' });
  }, function(){ window.gsap.set(element, { clearProps:'transform,opacity' }); });
}

export { animateAction, animateFeedback };
