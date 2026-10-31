import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

const out = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(out, '../../..')
const cases = [
  ['frontend/src/components/__codex_review_color.vue', '<template><p>review fixture</p></template><style scoped>p{color:#ff0000;background:rgba(255,190,140,.32)}</style>', true, 'ordinary Vue hex/rgb'],
  ['frontend/src/styles/__codex_review_color.css', '.review-fixture {color:#ff0000}', true, 'business CSS outside custom-property definition'],
  ['frontend/src/styles/__codex_review_color.js', 'export const reviewColor = "#ff0000"', true, 'non-token JS in styles directory'],
  ['frontend/src/components/bits/__codex_review_color.vue', '<template><p>review fixture</p></template><style scoped>p{color:#ff0000}</style>', true, 'new non-upstream component inside exempt directory'],
  ['frontend/src/components/__codex_review_color.vue', '<template><p>review fixture</p></template><style scoped>p{color:RGB(255 0 0)}</style>', true, 'valid uppercase CSS RGB'],
  ['frontend/src/components/__codex_review_color.vue', '<template><p>review fixture</p></template><style scoped>p{color:rgb(var(--rgb-white) / .5)}</style>', false, 'correct token usage'],
]
const results=[]
for(const [rel, content, mustReject, label] of cases){
  const target=path.join(root,rel)
  let created=false
  try{
    await fs.writeFile(target,content,{flag:'wx'}); created=true
    const r=spawnSync(process.execPath,['scripts/check-colors.mjs'],{cwd:root,encoding:'utf8'})
    results.push({label,path:rel,mustReject,exit:r.status,expectedBehavior:r.status===(mustReject?1:0),output:r.stdout+r.stderr})
  }finally{if(created)await fs.unlink(target)}
}
const base=spawnSync(process.execPath,['scripts/check-colors.mjs'],{cwd:root,encoding:'utf8'})
results.push({label:'post-cleanup baseline',exit:base.status,output:base.stdout+base.stderr})
await fs.writeFile(path.join(out,'color-results.json'),JSON.stringify(results,null,2))
console.log(JSON.stringify(results,null,2))
