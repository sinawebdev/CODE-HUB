const fs=require('fs');
const sp='C:/Users/HPLAPT~1/AppData/Local/Temp/claude/c--Users-HP-LAPTOP-Downloads-koforlink/696e98c8-2ba6-4753-9bcc-7e024a0265e0/scratchpad';
const {chromium}=require(sp+'/tools/node/node_modules/playwright-core');
const [base,email,password,directory]=process.argv.slice(2);
(async()=>{
 const response=await fetch(base+'/api/v1/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});
 const {data}=await response.json();if(!response.ok)throw Error('Test account login failed');
 fs.mkdirSync(directory,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1360,height:900}});
  await context.addInitScript(tokens=>{localStorage.setItem('kf_access',tokens.accessToken);localStorage.setItem('kf_refresh',tokens.refreshToken);},data);
  const page=await context.newPage();await page.goto(base+'/#/');await page.locator('#feed article.post').first().waitFor();
  await page.screenshot({path:directory+'/home-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:directory+'/home-mobile.png',fullPage:true});
  await page.setViewportSize({width:1360,height:900});await page.evaluate(()=>{location.hash='#/admin';});await page.locator('#adminStats .stat-value').first().waitFor();
  await page.screenshot({path:directory+'/admin-desktop.png',fullPage:true});
  await context.close();console.log('Saved desktop/mobile home and admin screenshots.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
