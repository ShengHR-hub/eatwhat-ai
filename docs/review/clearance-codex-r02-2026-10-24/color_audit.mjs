import fs from 'node:fs/promises'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import {createRequire} from 'node:module'
import {spawnSync} from 'node:child_process'
const out=path.dirname(fileURLToPath(import.meta.url)), root=path.resolve(out,'../../..')
const postcss=createRequire(path.join(root,'frontend/package.json'))('postcss')
const literal=/#(?:[\da-f]{3,8})\b|\b(?:rgba?|hsla?)\s*\((?!\s*var\()/i
const cssFiles=[]
async function walk(dir){for(const d of await fs.readdir(dir,{withFileTypes:true})){const p=path.join(dir,d.name);if(d.isDirectory())await walk(p);else if(/\.(css|vue)$/.test(p))cssFiles.push(p)}}
await walk(path.join(root,'frontend/src'))
const findings=[],declarations=[]
for(const file of cssFiles){
  const text=await fs.readFile(file,'utf8')
  const sections=file.endsWith('.vue')?[...text.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/g)].map(m=>m[1]):[text]
  for(const section of sections)postcss.parse(section,{from:file}).walkDecls(d=>{
    declarations.push({file:path.relative(root,file),selector:d.parent.selector,prop:d.prop,value:d.value,line:d.source.start.line})
    if(!d.prop.startsWith('--')&&literal.test(d.value))findings.push({file:path.relative(root,file),line:d.source.start.line,prop:d.prop,value:d.value})
  })
}
const tokens=Object.fromEntries(declarations.filter(d=>d.prop.startsWith('--')).map(d=>[d.prop,d.value]))
function resolved(value){return value.replace(/var\((--[\w-]+)\)/g,(m,k)=>tokens[k]??m)}
function canon(value){return value.replace(/rgba?\(\s*([\d.]+)(?:\s*,\s*|\s+)([\d.]+)(?:\s*,\s*|\s+)([\d.]+)(?:\s*[,/]\s*([\d.]+))?\s*\)/gi,(_,r,g,b,a)=>`rgba(${+r},${+g},${+b},${a===undefined?1:+a})`).replace(/\s+/g,' ').trim()}
const old=JSON.parse(await fs.readFile(path.join(root,'docs/review/clearance-codex-2026-10-24/css-outside-token-definitions.json'),'utf8'))
const materialChecks=old.map(item=>{
  const filename=item.path.replaceAll('\\','/'), all=declarations.filter(d=>d.file.replaceAll('\\','/')===filename&&d.prop===item.property&&!d.prop.startsWith('--'))
  const matches=all.filter(d=>canon(resolved(d.value))===canon(item.value))
  return {old:item,matchingCurrent:matches,valuesUnchanged:matches.length>0}
})
const production=spawnSync(process.execPath,[path.join(root,'scripts/check-colors.mjs')],{encoding:'utf8'})
const sandbox=path.join(out,'color-sandbox')
await fs.mkdir(path.join(sandbox,'scripts'),{recursive:true})
await fs.mkdir(path.join(sandbox,'frontend/src/components/bits'),{recursive:true})
await fs.mkdir(path.join(sandbox,'frontend/src/styles'),{recursive:true})
await fs.mkdir(path.join(sandbox,'frontend/src/utils'),{recursive:true})
await fs.copyFile(path.join(root,'scripts/check-colors.mjs'),path.join(sandbox,'scripts/check-colors.mjs'))
const cases=[
  ['hex-upper','styles/probe.css','.x { color: #ABCDEF; }',1],
  ['rgb-upper','styles/probe.css','.x { color: RGB(255 0 0); }',1],
  ['hsla-upper','styles/probe.css','.x { color: HSLA(10,20%,30%,.5); }',1],
  ['js','probe.js','export const color = "#ff0000"',1],
  ['vue','probe.vue','<template><div style="color:#ff0000" /></template>',1],
  ['bits-business','components/bits/BusinessCard.vue','<style>.x{color:#00ff00}</style>',1],
  ['universal-selector','styles/probe.css','* { color: #ff0000; }',1],
  ['comment-prefix','styles/probe.css','/* normal comment */ .x { color: #ff0000; }',1],
  ['token-followed-by-business','styles/probe.css',':root {\n  --approved: #fff; color: #ff0000;\n}',1],
  ['local-token-in-component','components/bits/BusinessCard.vue','<style scoped>\n.x {\n --local-red: #ff0000;\n color: var(--local-red);\n}\n</style>',1],
  ['legal-token','styles/probe.css',':root {\n --approved: #fff;\n}\n.x { color: rgb(var(--rgb-white) / .5); }',0],
  ['legal-comment','styles/probe.css','/* #ff0000 RGB(255 0 0) */\n.x {color:var(--approved)}',0],
  ['upstream-exact','components/bits/Grainient.vue','<style>.x{color:#00ff00}</style>',0],
]
const probes=[]
for(const [name,rel,content,expected] of cases){
  const file=path.join(sandbox,'frontend/src',rel)
  await fs.writeFile(file,content)
  try{const p=spawnSync(process.execPath,[path.join(sandbox,'scripts/check-colors.mjs')],{encoding:'utf8'});probes.push({name,fixture:rel,content,expected,actual:p.status,correct:p.status===expected,output:p.stdout+p.stderr})}
  finally{await fs.unlink(file)}
}
const after=spawnSync(process.execPath,[path.join(sandbox,'scripts/check-colors.mjs')],{encoding:'utf8'})
const report={production:{exit:production.status,output:production.stdout+production.stderr},astBusinessLiteralFindings:findings,materialChecks,
  fiveTokens:Object.fromEntries(Object.entries(tokens).filter(([k])=>k.startsWith('--rgb-glass-'))),probes,sandboxCleanup:{exit:after.status,output:after.stdout+after.stderr}}
await fs.writeFile(path.join(out,'color-results.json'),JSON.stringify(report,null,2))
console.log(JSON.stringify({production:report.production,astBusinessLiteralCount:findings.length,materialChecks:materialChecks.map(c=>({path:c.old.path,line:c.old.line,unchanged:c.valuesUnchanged})),fiveTokens:report.fiveTokens,probes:probes.map(({name,expected,actual,correct})=>({name,expected,actual,correct})),cleanup:report.sandboxCleanup},null,2))
