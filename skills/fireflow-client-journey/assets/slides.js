/* === Linear journey navigation: buttons, keyboard, swipe and browser history === */
(() => {
 'use strict';
 const data=JSON.parse(document.getElementById('slide-data').textContent),slides=[...document.querySelectorAll('.slide')];
 let current=0;
 const next=document.getElementById('next'),previous=document.getElementById('previous');
 function show(index,{focus=false,history=false}={}){
  current=Math.max(0,Math.min(slides.length-1,index));
  document.querySelector('.deck-viewport').classList.toggle('is-start',current===0);
  slides.forEach((slide,i)=>{slide.classList.toggle('active',i===current);slide.setAttribute('aria-hidden',String(i!==current));slide.inert=i!==current;});
  previous.disabled=current===0;next.classList.toggle('restart',current===slides.length-1);
  document.getElementById('position-number').textContent=String(current+1).padStart(2,'0')+' / '+slides.length;
  document.getElementById('chapter-name').textContent=data[current].chapter;
  document.getElementById('next-topic').textContent=current<slides.length-1?'Next: '+data[current+1].title:'Explore the full view or restart the journey.';
  document.getElementById('next-label').textContent=current===slides.length-1?'Restart':'Next';
  next.setAttribute('aria-label',current===slides.length-1?'Restart the journey':'Next screen: '+data[current+1].title);
  document.getElementById('progress-fill').style.width=(current+1)/slides.length*100+'%';
  document.querySelector('[role="progressbar"]').setAttribute('aria-valuenow',current+1);
  document.getElementById('announcement').textContent='Screen '+(current+1)+' of '+slides.length+'. '+data[current].title;
  document.title='FireFlow | '+data[current].title;
  if(history){try{window.history.pushState(null,'','#'+data[current].id)}catch(e){}}
  if(focus)slides[current].querySelector('h1').focus({preventScroll:true});
 }
 function move(by){show(current+by,{focus:true,history:true})}
 next.addEventListener('click',()=>show(current===slides.length-1?0:current+1,{focus:true,history:true}));
 previous.addEventListener('click',()=>move(-1));
 function fromHash(){const i=data.findIndex(s=>s.id===location.hash.slice(1));show(i<0?0:i)}
 window.addEventListener('hashchange',fromHash);window.addEventListener('popstate',fromHash);
 document.addEventListener('keydown',e=>{
  if(e.altKey||e.ctrlKey||e.metaKey||e.target.closest('input,textarea,select,[contenteditable="true"]'))return;
  if(e.key===' '&&e.target.closest('button,a'))return;
  if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key)){e.preventDefault();move(1)}
  else if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();move(-1)}
  else if(e.key==='Home'){e.preventDefault();show(0,{focus:true,history:true})}
  else if(e.key==='End'){e.preventDefault();show(slides.length-1,{focus:true,history:true})}
 });
 let touch=null;const stage=document.getElementById('deck-stage');
 stage.addEventListener('touchstart',e=>{if(e.touches.length===1&&!e.target.closest('a,button'))touch={x:e.touches[0].clientX,y:e.touches[0].clientY};else touch=null},{passive:true});
 stage.addEventListener('touchend',e=>{if(!touch)return;const dx=e.changedTouches[0].clientX-touch.x,dy=e.changedTouches[0].clientY-touch.y;touch=null;if(Math.abs(dx)>60&&Math.abs(dx)>Math.abs(dy)*1.5)move(dx<0?1:-1)},{passive:true});
 /* A deliberate wheel gesture advances one screen; trackpad inertia never skips screens. */
 let wheel=0,lastWheel=0,lastMove=-Infinity;
 stage.addEventListener('wheel',e=>{if(e.ctrlKey)return;e.preventDefault();const now=performance.now();if(now-lastWheel>180)wheel=0;lastWheel=now;if(now-lastMove<850)return;wheel+=e.deltaY;if(Math.abs(wheel)>90){move(wheel>0?1:-1);wheel=0;lastMove=now}},{passive:false});
 /* === Preserve the user's theme across the guided and complete views === */
 function theme(value){document.documentElement.dataset.theme=value;const target=value==='dark'?'light':'dark',button=document.getElementById('theme-toggle');button.setAttribute('aria-label','Switch to '+target+' mode');button.querySelector('span').textContent=target==='light'?'Light mode':'Dark mode';button.querySelector('use').setAttribute('href',target==='light'?'#sun':'#moon')}
 document.getElementById('theme-toggle').addEventListener('click',()=>{const value=document.documentElement.dataset.theme==='dark'?'light':'dark';theme(value);try{localStorage.setItem('fireflow-theme',value)}catch(e){}});
 theme(document.documentElement.dataset.theme);fromHash();
})();
