import fs from 'node:fs/promises'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import {Script,createContext} from 'node:vm'
import {createRequire} from 'node:module'
const out=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(out,'../../..')
const postcss=createRequire(path.join(root,'frontend/package.json'))('postcss')
const report=JSON.parse(await fs.readFile(path.join(out,'color-results.json'),'utf8'))
const cases=report.probes.filter(p=>['regex-char-class-js','url-double-slash-css'].includes(p.name))
const result=cases.map(p=>{
  if(p.name==='regex-char-class-js'){
    const context=createContext({})
    new Script(p.content+'; globalThis.reviewColor=color;').runInContext(context)
    return {name:p.name,source:p.content,syntaxValid:true,actualAssignedColor:context.reviewColor,checkerExit:p.actual}
  }
  const ast=postcss.parse(p.content)
  const decls=[];ast.walkDecls(d=>decls.push({prop:d.prop,value:d.value}))
  return {name:p.name,source:p.content,syntaxValid:true,declarations:decls,checkerExit:p.actual}
})
await fs.writeFile(path.join(out,'syntax-results.json'),JSON.stringify(result,null,2))
console.log(JSON.stringify(result,null,2))
