const fs = require('fs');
const path = require('path');
const sp = 'C:/Users/HPLAPT~1/AppData/Local/Temp/claude/c--Users-HP-LAPTOP-Downloads-koforlink/696e98c8-2ba6-4753-9bcc-7e024a0265e0/scratchpad';
const acorn = require(sp+'/tools/node/node_modules/acorn');
const html = fs.readFileSync(sp+'/data/Index.html','utf8');
let source = html.slice(html.lastIndexOf('<script>')+8,html.lastIndexOf('</script>'));
const tree = acorn.parse(source,{ecmaVersion:'latest',locations:true});
const groups = {core:[],router:[],layout:[],main:[],auth:[],home:[],feed:[],network:[],jobs:[],companies:[],events:[],messages:[],notifications:[],profile:[],settings:[],search:[],admin:[]};
function group(line){
 if(line<=213)return 'core'; if(line<=292)return 'router'; if(line<=442)return 'layout'; if(line<=456)return 'main';
 if(line<=767)return 'auth'; if(line<=791)return 'layout'; if(line<=1066)return 'home'; if(line<=1447)return 'feed';
 if(line<=1542)return 'network'; if(line<=1851)return 'jobs'; if(line<=2253)return 'companies'; if(line<=2340)return 'events';
 if(line<=2491)return 'messages'; if(line<=2521)return 'notifications'; if(line<=2840)return 'profile'; if(line<=2899)return 'settings';
 if(line<=2940)return 'search'; if(line<=2965)return 'feed'; if(line<=3206)return 'admin'; return 'main';
}
for(const n of tree.body){
 const name=n.id?.name || n.declarations?.[0]?.id.name;
 if(['__kfReady','TOKEN_KEY','api','setToken','fileToBase64'].includes(name))continue;
 groups[group(n.loc.start.line)].push(source.slice(n.start,n.end));
}
const special = {apiResendOTP:'resendCode',apiChangeUnverifiedEmail:'changeEmail',apiUploadAvatar:'uploadAvatar'};
function mapped(name){return special[name] || name.slice(3,4).toLowerCase()+name.slice(4);}
function walk(n,cb){if(!n||typeof n!=='object')return; if(n.type)cb(n); for(const [k,v] of Object.entries(n)){if(k==='loc')continue;if(Array.isArray(v))v.forEach(x=>walk(x,cb));else if(v&&typeof v==='object')walk(v,cb);}}
const coverage=[];
for(const [key,chunks] of Object.entries(groups)){
 let s=chunks.join('\n\n');
 // Upload the browser File directly instead of producing base64 strings.
 s=s.replace(/(?:return )?fileToBase64\((\w+)\)\.then\(function\((?:b64|base64)\)\{\s*(?:var folder = ([^;]+);\s*)?return api\.call\('apiUploadFile', api\.token\(\), ([^,]+), \1\.name, \1\.type, (?:b64|base64)\);\s*\}\)/g,(all,file,folder,argument)=> `${all.startsWith('return ')?'return ':''}api.uploadFile(${folder||argument}, ${file})`);
 const parsed=acorn.parse(s,{ecmaVersion:'latest'}), edits=[];
 walk(parsed,n=>{
  if(n.type==='CallExpression'&&n.callee.type==='MemberExpression'&&n.callee.object.name==='api'&&n.callee.property.name==='call'){
   const name=n.arguments[0].value, fn=mapped(name); let args=n.arguments.slice(1);
   if(args[0]?.type==='CallExpression'&&args[0].callee.object?.name==='api'&&args[0].callee.property?.name==='token')args=args.slice(1);
   coverage.push({demo:name,function:fn,module:key});
   edits.push([n.start,n.end,`api.${fn}(${args.map(a=>s.slice(a.start,a.end)).join(', ')})`]);
  }
 });
 for(const [a,b,replacement] of edits.sort((a,b)=>b[0]-a[0]))s=s.slice(0,a)+replacement+s.slice(b);
 s=s.replace(/__kfReady/g,'State.ready').replace(/setToken\(res\.data\.token\)/g,'api.setTokens(res.data.accessToken, res.data.refreshToken)').replace(/setToken\(''\)/g,'api.clearTokens()');
 if(key==='core'){
  s=s.replace(' onclick="event.stopPropagation()"','');
  s+=`\n\nfunction navigate(hash){ if(location.hash === hash) rerender(); else location.hash = hash; }\nfunction rerender(){ window.dispatchEvent(new Event('hashchange')); }\n`;
 }
 if(key==='layout')s=s.replace('if (State.user) router();','if (State.user) rerender();');
 if(key==='main'){
  s=s.replace('if (location.hash === target) router(); else location.hash = target;','navigate(target);');
  s=`window.addEventListener('kf:signed-out', function(){\n  if(State.chatPoll) clearInterval(State.chatPoll);\n  Object.assign(State, {user:null, emailVerified:false, profilePhoto:'', isStaff:false, isAdmin:false, currentChat:null, counts:{notifications:0,messages:0,connectionRequests:0}, cache:{}});\n  navigate('#/login');\n});\nwindow.addEventListener('kf:verify-email', function(){ navigate('#/verify-email'); });\n\n`+s;
 }
 if(key==='auth'){
  s=s.replace("location.hash = '#/verify-email';\n      } else {\n        location.hash = '#/';\n      }\n      router();","navigate('#/verify-email');\n      } else {\n        navigate('#/');\n      }");
  s=s.replace(/location\.hash = ('#\/(?:verify-email)?');\n      router\(\);/g,'navigate($1);');
  const a=s.indexOf("  $('#forgotLink').onclick"), b=s.indexOf('\n}\n',a);
  s=s.slice(0,a)+`  $('#forgotLink').onclick = function(ev){ ev.preventDefault(); openPasswordResetModal(); };`+s.slice(b);
  s+=`\n\nfunction openPasswordResetModal(){\n  openModal({title:'Reset password',size:'sm',\n    body:'<p class="muted small mb-3">Enter your email address and we will send a reset code.</p><input id="resetEmail" class="input" type="email" placeholder="you@example.com">',\n    footer:'<button class="btn btn-ghost" data-close>Cancel</button><button class="btn btn-primary" id="resetBtn">Send code</button>'});\n  $('#resetBtn').onclick = async function(){\n    var email=$('#resetEmail').value.trim(), btn=this;\n    if(!email) return toast('Enter your email','error');\n    btn.disabled=true;\n    try {\n      await api.requestPasswordReset(email);\n      closeAllModals();\n      openModal({title:'Reset password',size:'sm',\n        body:'<p class="muted small mb-3">Enter the code sent to your email and choose a new password.</p><div class="field"><label>Reset code</label><input id="resetCode" class="input" inputmode="numeric" maxlength="6" autocomplete="one-time-code"></div><div class="field"><label>New password</label><input id="resetPassword" class="input" type="password" minlength="8" autocomplete="new-password"></div>',\n        footer:'<button class="btn btn-ghost" data-close>Cancel</button><button class="btn btn-primary" id="resetConfirm">Update password</button>'});\n      $('#resetConfirm').onclick=async function(){\n        var code=$('#resetCode').value.trim(), password=$('#resetPassword').value, confirm=this;\n        if(!/^\\d{6}$/.test(code))return toast('Enter the 6-digit code','error');\n        if(password.length<8)return toast('Password must be at least 8 characters.','error');\n        confirm.disabled=true;\n        try{await api.confirmPasswordReset(email,code,password);toast('Password updated. You can now sign in.');closeAllModals();}\n        catch(e){toast(e.message,'error');confirm.disabled=false;}\n      };\n    } catch(e){toast(e.message,'error');btn.disabled=false;}\n  };\n}\n`;
 }
 if(key==='events')s=s.replace("maxAttendees: $('#evMax').value", "maxAttendees: Number($('#evMax').value || 0)");
 if(key==='companies')s=s.replace("((loc && loc.latitude) || '')", "(loc?.latitude ?? '')").replace("((loc && loc.longitude) || '')", "(loc?.longitude ?? '')");
 if(key==='home')s=s.replace("$('#composeTrigger').onclick = function(){ openComposer(); };","$('#composeTrigger').onclick = function(e){ if(e.target.closest('button,a'))return; openComposer(); };");
 if(key==='messages'){
  s=s.replace("scroll.insertAdjacentHTML('beforeend', msgBlock(res.data));","if (!Array.from(scroll.querySelectorAll('[data-msg]')).some(function(el){return el.dataset.msg === res.data.id;})) scroll.insertAdjacentHTML('beforeend', msgBlock(res.data));");
  s=s.replace("if (messages.length) { messages.forEach(function(m){ scroll.insertAdjacentHTML('beforeend', msgBlock(m)); }); scroll.scrollTop = scroll.scrollHeight; }",`if(State.currentChat !== convId || scroll !== $('#chatScroll'))return;\n    var existing=new Set(Array.from(scroll.querySelectorAll('[data-msg]')).map(function(el){return el.dataset.msg;}));\n    var fresh=messages.filter(function(m){if(existing.has(m.id))return false;existing.add(m.id);return true;});\n    if (fresh.length) { var empty=scroll.querySelector('.empty');if(empty)empty.remove();fresh.forEach(function(m){ scroll.insertAdjacentHTML('beforeend', msgBlock(m)); }); scroll.scrollTop = scroll.scrollHeight; }`);
 }
 if(key==='admin'){
  s=s.replace("openAdminUserMenu(b.getAttribute('data-admin-user'));","var row=list.find(function(item){return item.UserID===b.getAttribute('data-admin-user');});openAdminUserMenu(row.UserID,row.Role,row.Status,row.FullName || ((row.FirstName||'')+' '+(row.LastName||''))); ");
  s=s.replace('function openAdminUserMenu(userId){','function openAdminUserMenu(userId, currentRole, currentStatus, name){').replace("title:'Manage user', size:'sm',","title:'Manage user', size:'sm',");
  s=s.replace("body:'<div class=\"field\"><label>Role</label>'", "body:'<p class=\"mb-3\">' + esc(name||userId) + '</p><div class=\"field\"><label>Role</label>'");
  s=s.replace("return '<option>' + r + '</option>';","return '<option ' + (r===currentRole?'selected':'') + '>' + r + '</option>'; ").replace("return '<option>' + s + '</option>';","return '<option ' + (s===currentStatus?'selected':'') + '>' + s + '</option>'; ");
  s=s.replace("api.adminSetUserRole(userId, $('#auRole').value).then(function(){\n      return api.adminSetUserStatus(userId, $('#auStatus').value);\n    }).then(function(){ closeAllModals(); toast('Updated'); })",`var role=$('#auRole').value, status=$('#auStatus').value, btn=this;btn.disabled=true;\n    Promise.resolve().then(function(){if(role!==currentRole)return api.adminSetUserRole(userId,role);})\n      .then(function(){if(status!==currentStatus)return api.adminSetUserStatus(userId,status);})\n      .then(function(){closeAllModals();toast('Updated');loadAdminList('users');})`);
  s=s.replace(".catch(function(e){ toast(e.message||'Failed', 'error'); });\n  };\n}\n\nfunction loadAdminSettings", ".catch(function(e){ toast(e.message||'Failed', 'error'); btn.disabled=false; });\n  };\n}\n\nfunction loadAdminSettings");
 }
 groups[key]=s;
}
// Discover all top-level exports, then add explicit imports for shared symbols.
const symbols=new Map();
for(const [key,s] of Object.entries(groups))for(const n of acorn.parse(s,{ecmaVersion:'latest'}).body){
 if(n.type==='FunctionDeclaration')symbols.set(n.id.name,key);
 if(n.type==='VariableDeclaration')for(const d of n.declarations)symbols.set(d.id.name,key);
}
fs.mkdirSync('frontend/js',{recursive:true});fs.mkdirSync('frontend/css',{recursive:true});
for(const [key,s] of Object.entries(groups)){
 const imports=new Map();
 walk(acorn.parse(s,{ecmaVersion:'latest'}),n=>{if(n.type!=='Identifier')return;const owner=symbols.get(n.name);if(owner&&owner!==key){if(!imports.has(owner))imports.set(owner,new Set());imports.get(owner).add(n.name);}});
 let head='// Ported from the original KoforLink demo; HTTP transport is in api.js.\n';
 if(s.includes('api.'))head+="import * as api from './api.js';\n";
 for(const [owner,names]of imports)head+=`import { ${[...names].sort().join(', ')} } from './${owner}.js';\n`;
 const exports=[...symbols].filter(([,owner])=>owner===key).map(([name])=>name);
 fs.writeFileSync('frontend/js/'+key+'.js',head+'\n'+s+'\n'+(exports.length?'\nexport { '+exports.join(', ')+' };\n':''));
}
const css=html.slice(html.indexOf('<style>')+7,html.indexOf('</style>')).trim();
fs.writeFileSync('frontend/css/main.css',css+'\n.avatar-44{width:44px;height:44px;font-size:16px}\n.comment{display:flex;gap:10px;align-items:flex-start}\n.comment-body{flex:1;min-width:0;background:var(--surface-2);border-radius:var(--r);padding:8px 12px}\n.comment-author{font-weight:600;font-size:13px}\n.comment-text{font-size:13.5px;line-height:1.55;white-space:pre-wrap;word-break:break-word}\n');
let markup=html.slice(0,html.lastIndexOf('<script>'))+'<script type="module" src="js/main.js"></script>\n</body>\n</html>\n';
markup=markup.replace(/<style>[\s\S]*?<\/style>/,'<meta name="api-base" content="/api/v1">\n<link rel="stylesheet" href="css/main.css">').replace('Unable to initialize the application.</p>','Cannot reach the KoforLink server.</p>');
markup=markup.replace('</title>',`</title>\n<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Crect width='48' height='48' rx='12' fill='%230E7C4A'/%3E%3Ctext x='24' y='30' text-anchor='middle' font-family='sans-serif' font-weight='700' font-size='21' fill='white'%3EKL%3C/text%3E%3C/svg%3E">`);
fs.writeFileSync('frontend/index.html',markup);
fs.writeFileSync('tools/frontend-port/coverage.json',JSON.stringify(coverage));
console.log('Ported '+coverage.length+' API call sites plus direct file uploads.');
