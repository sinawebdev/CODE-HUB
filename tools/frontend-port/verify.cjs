const fs=require('fs'), path=require('path'), http=require('http');
const sp='C:/Users/HPLAPT~1/AppData/Local/Temp/claude/c--Users-HP-LAPTOP-Downloads-koforlink/696e98c8-2ba6-4753-9bcc-7e024a0265e0/scratchpad';
const acorn=require(sp+'/tools/node/node_modules/acorn');
const {chromium}=require(sp+'/tools/node/node_modules/playwright-core');
function walk(n,cb){if(!n||typeof n!=='object')return;if(n.type)cb(n);for(const [k,v]of Object.entries(n)){if(k==='loc')continue;if(Array.isArray(v))v.forEach(x=>walk(x,cb));else if(v&&typeof v==='object')walk(v,cb);}}
const files=fs.readdirSync('frontend/js').filter(f=>f.endsWith('.js')), parsed={}, exportedNames={};
for(const file of files){const s=fs.readFileSync('frontend/js/'+file,'utf8');parsed[file]=acorn.parse(s,{sourceType:'module',ecmaVersion:'latest'});exportedNames[file]=new Set();for(const n of parsed[file].body)if(n.type==='ExportNamedDeclaration'){for(const spec of n.specifiers)exportedNames[file].add(spec.exported.name);if(n.declaration?.id)exportedNames[file].add(n.declaration.id.name);for(const d of n.declaration?.declarations||[])exportedNames[file].add(d.id.name);}if(s.split('\n').length>=500)throw Error('Too many lines: '+file);if(/api\.call\(|google\.script|fileToBase64|api\.token\(/.test(s))throw Error('Legacy transport: '+file);}
for(const [file,tree]of Object.entries(parsed))for(const n of tree.body)if(n.type==='ImportDeclaration'){const target=path.basename(n.source.value);if(!exportedNames[target])throw Error('Missing import file '+target);for(const spec of n.specifiers)if(spec.type==='ImportSpecifier'&&!exportedNames[target].has(spec.imported.name))throw Error(file+' missing '+spec.imported.name+' from '+target);}
const original=fs.readFileSync(sp+'/data/Index.html','utf8'), coverage=JSON.parse(fs.readFileSync('tools/frontend-port/coverage.json','utf8'));
const names=[...original.matchAll(/api\.call\('([^']+)'/g)].map(m=>m[1]);
const used=new Map();for(const [file,tree]of Object.entries(parsed))walk(tree,n=>{if(n.type==='CallExpression'&&n.callee.object?.name==='api'){const fn=n.callee.property.name;used.set(fn,(used.get(fn)||0)+1);if(!exportedNames['api.js'].has(fn))throw Error('Missing API export '+fn);}});
for(const {demo,function:fn}of coverage)if(!exportedNames['api.js'].has(fn)||!used.has(fn))throw Error('Unmapped API '+demo);
 if(names.length!==coverage.length+used.get('uploadFile'))throw Error('Call site count mismatch');
console.log(JSON.stringify({syntaxModules:files.length,importCoverage:'pass',demoCallSites:names.length,mapped:coverage.length,fileUploads:used.get('uploadFile'),apiExports:exportedNames['api.js'].size}));
const server=http.createServer((req,res)=>{const target=path.resolve('frontend','.'+new URL(req.url,'http://localhost').pathname);const root=path.resolve('frontend');if(!target.startsWith(root)){res.writeHead(403);return res.end();}let file=target;if(fs.existsSync(file)&&fs.statSync(file).isDirectory())file=path.join(file,'index.html');if(!fs.existsSync(file)){res.writeHead(404,{'Content-Type':'application/json'});return res.end('{"detail":"No API server"}');}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html');fs.createReadStream(file).pipe(res);});
(async()=>{await new Promise(resolve=>server.listen(5590,'127.0.0.1',resolve));let browser;try{browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage();const errors=[], localFailures=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.url().includes('127.0.0.1')&&!r.url().includes('/api/')&&r.status()>=400)localFailures.push(r.url());});await page.goto('http://127.0.0.1:5590');await page.waitForSelector('#landing:not(.hidden)');await page.goto('http://127.0.0.1:5590/#/login');await page.waitForSelector('#loginForm');await page.goto('http://127.0.0.1:5590/#/register');await page.waitForSelector('#regForm');if(errors.length||localFailures.length)throw Error(JSON.stringify({errors,localFailures}));console.log('Browser: offline landing, login and registration render; no module/import/resource errors.');
 const result=await page.evaluate(async()=>{
  const api=await import('/js/api.js');let calls=[],refreshes=0;
  const originalFetch=window.fetch;
  window.fetch=async(url,opts)=>{calls.push({path:new URL(String(url),location.origin).pathname,method:opts.method,body:opts.body,authorization:opts.headers.Authorization});if(String(url).endsWith('/auth/refresh')){refreshes++;await new Promise(r=>setTimeout(r,30));return Response.json({data:{accessToken:'new-access',refreshToken:'new-refresh'}});}if(opts.headers.Authorization==='Bearer old-access')return Response.json({detail:'expired',code:'TOKEN_EXPIRED'},{status:401});return Response.json({data:{ok:true},message:'OK'});};
  api.setTokens('old-access','old-refresh');await Promise.all([api.getFeed({offset:0,limit:20}),api.getSuggestions(4)]);
  if(refreshes!==1)throw Error('Refresh was not shared');
  if(localStorage.getItem('kf_refresh')!=='new-refresh')throw Error('Tokens not rotated');
  calls=[];await api.adminSetUserStatus('USR-test','Active');if(JSON.parse(calls[0].body).status!=='Active')throw Error('Status mapping failed');
  let signedOut=0;window.addEventListener('kf:signed-out',()=>signedOut++);api.setTokens('old-access','broken');window.fetch=async()=>Response.json({detail:'expired',code:'TOKEN_EXPIRED'},{status:401});try{await api.getSession();throw Error('Expected failed refresh');}catch(e){if(e.code!=='AUTH_REQUIRED')throw e;}if(signedOut!==1||api.hasSession())throw Error('Failed refresh did not sign out');
  window.fetch=originalFetch;return {sharedRefresh:true,rotation:true,failedRefreshSignsOut:true};
 });console.log('HTTP client: '+JSON.stringify(result));
 const behavior=await page.evaluate(async()=>{
  const core=await import('/js/core.js'), auth=await import('/js/auth.js'), admin=await import('/js/admin.js'), home=await import('/js/home.js'), messages=await import('/js/messages.js');
  const originalFetch=window.fetch, writes=[];
  window.fetch=async(url,opts)=>{
    const pathname=new URL(String(url),location.origin).pathname;
    if(opts.method!=='GET')writes.push({pathname,body:opts.body});
    let data=[];
    if(pathname.endsWith('/feed'))data={posts:[],hasMore:false};
    if(pathname.endsWith('/trending'))data={posts:[],skills:[]};
    if(pathname.endsWith('/platform/bootstrap'))data={authenticated:false,settings:{}};
    if(pathname.endsWith('/messages'))data={messages:[{id:'MSG-one',body:'Hello',mine:false},{id:'MSG-one',body:'Hello',mine:false}],conversation:{}};
    return Response.json({data,message:'OK'});
  };
  const settle=()=>new Promise(r=>setTimeout(r,80));
  core.openModal({title:'Close check',body:'Body'});document.querySelector('.overlay [data-close]').click();await settle();if(document.querySelector('.overlay'))throw Error('Close control blocked by modal propagation');
  admin.openAdminUserMenu('USR-test','Professional','Active','Test Member');
  if(document.querySelector('#auRole').value!=='Professional'||document.querySelector('#auStatus').value!=='Active')throw Error('Admin defaults unsafe');
  document.querySelector('#auSave').click();await settle();if(writes.length)throw Error('Unchanged admin fields were written');
  admin.openAdminUserMenu('USR-test','Professional','Active','Test Member');document.querySelector('#auStatus').value='Suspended';document.querySelector('#auSave').click();await settle();
  if(writes.length!==1||!writes[0].pathname.endsWith('/status'))throw Error('Admin saved unchanged role');
  writes.length=0;auth.openPasswordResetModal();document.querySelector('#resetEmail').value='member@example.com';document.querySelector('#resetBtn').click();await settle();
  if(!document.querySelector('#resetCode'))throw Error('Reset code step absent');document.querySelector('#resetCode').value='123456';document.querySelector('#resetPassword').value='password123';document.querySelector('#resetConfirm').click();await settle();
  if(writes.length!==2||!writes[1].pathname.endsWith('/password-reset/confirm'))throw Error('Reset confirmation absent');
  core.State.user={UserID:'USR-test',FirstName:'Test',LastName:'Member',FullName:'Test Member',Role:'Professional'};core.State.emailVerified=true;
  home.renderHome();document.querySelector('#composeTrigger .composer-tools [data-new-post]').click();if(document.querySelectorAll('.overlay').length!==1)throw Error('Photo button expected one composer, found '+document.querySelectorAll('.overlay').length+' ('+Array.from(document.querySelectorAll('.modal-head h2')).map(e=>e.textContent).join(',')+')');core.closeAllModals();
  document.querySelector('#composeTrigger [data-goto="#/jobs"]').click();if(document.querySelectorAll('.overlay').length)throw Error('Job button opened composer');await settle();
  document.querySelector('#main').innerHTML='<div id="chatScroll"><div class="empty">No messages yet</div></div>';core.State.currentChat='CON-test';messages.pollMessages();await settle();messages.pollMessages();await settle();
  if(document.querySelectorAll('#chatScroll [data-msg]').length!==1||document.querySelector('#chatScroll .empty'))throw Error('Polling dedupe or placeholder failed');
  window.fetch=originalFetch;core.State.user=null;core.State.currentChat=null;
  return {adminPreservesRole:true,resetTwoSteps:true,composerClickGuard:true,messagePollDedupe:true};
 });console.log('Behavior: '+JSON.stringify(behavior));if(errors.length)throw Error('Page errors: '+errors.join('; '));
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}})().catch(e=>{console.error(e);process.exitCode=1;});
