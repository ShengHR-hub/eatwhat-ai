import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
const out=path.dirname(fileURLToPath(import.meta.url))
const root=path.resolve(out,'../../..')
const require=createRequire(path.join(root,'frontend/package.json'))
const postcss=require('postcss')
const findings=[]
for(const name of await fs.readdir(path.join(root,'frontend/src/styles'))){
  if(!name.endsWith('.css'))continue
  const filename=path.join(root,'frontend/src/styles',name)
  postcss.parse(await fs.readFile(filename,'utf8'),{from:filename}).walkDecls(d=>{
    if(d.prop.startsWith('--'))return
    if(/#[\da-f]{3,8}\b|\brgba?\s*\(\s*\d/i.test(d.value))findings.push({path:path.relative(root,filename),line:d.source.start.line,property:d.prop,value:d.value})
  })
}
await fs.writeFile(path.join(out,'css-outside-token-definitions.json'),JSON.stringify(findings,null,2))
console.log(JSON.stringify(findings,null,2))
