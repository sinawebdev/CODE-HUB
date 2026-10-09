const fs = require('fs');
const sp = 'C:/Users/HPLAPT~1/AppData/Local/Temp/claude/c--Users-HP-LAPTOP-Downloads-koforlink/696e98c8-2ba6-4753-9bcc-7e024a0265e0/scratchpad';
const acorn = require(sp+'/tools/node/node_modules/acorn');
const html = fs.readFileSync(sp+'/data/Index.html','utf8');
const script = html.slice(html.lastIndexOf('<script>')+8,html.lastIndexOf('</script>'));
for(const n of acorn.parse(script,{ecmaVersion:'latest',locations:true}).body) console.log(n.loc.start.line,n.loc.end.line,n.type,n.id?.name || n.declarations?.map(d=>d.id.name).join(',') || script.slice(n.start,n.start+70).replace(/\n/g,' '));
