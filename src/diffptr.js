const fs=require("fs"), vm=require("vm"), path=require("path");
const html=fs.readFileSync(path.join(__dirname,"..","index.html"),"utf8");
const blocks=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
const noop=()=>{};
const ctx=new Proxy({},{get:(t,k)=>k==="createLinearGradient"?()=>({addColorStop:noop}):k==="measureText"?()=>({width:10}):(t[k]!==undefined?t[k]:noop),set:(t,k,v)=>{t[k]=v;return true}});
function el(){const e={style:{},dataset:{},clientWidth:900,clientHeight:400,width:900,height:400,textContent:"",innerHTML:"",value:"0",max:"100",min:"0",className:"",addEventListener:noop,setAttribute:noop,getAttribute:()=>null,setPointerCapture:noop,classList:{add:noop,remove:noop,contains:()=>false},getBoundingClientRect:()=>({left:0,top:0,width:900,height:400}),getContext:()=>ctx,closest:()=>null,querySelectorAll:()=>[],dispatchEvent:noop};e.parentNode={clientWidth:900,getBoundingClientRect:()=>({left:0,top:0,width:900,height:400})};return e}
const m=new Map();
const sb={document:{documentElement:{getAttribute:()=>null},getElementById:i=>{if(!m.has(i))m.set(i,el());return m.get(i)},querySelectorAll:()=>[],createElement:el,addEventListener:noop},console,
atob:s=>Buffer.from(s,"base64").toString("binary"),matchMedia:()=>({matches:false,addEventListener:noop}),
getComputedStyle:()=>({getPropertyValue:()=>"#888"}),devicePixelRatio:2,requestAnimationFrame:noop,
performance:{now:()=>0},addEventListener:noop,setTimeout:noop,Math,JSON,Map,Set,isFinite,parseInt,parseFloat,Intl,
Float32Array,Int16Array,Uint8Array,Uint16Array,Uint32Array,Float64Array};
sb.window=sb; vm.createContext(sb);
blocks.forEach(b=>{try{vm.runInContext(b,sb)}catch(e){}});
const {S,PTR,NS,M}=vm.runInContext("({S,PTR,NS,M})",sb);
const YEAR=+process.argv[2]||1009;
const out={};
for(let s=0;s<NS;s++){
  const i=YEAR-S.y0[s];
  if(i<0||i>=S.len[s])continue;
  const p=PTR[S.off[s]+i];
  if(isFinite(p)) out[S.code[s]]=p;
}
fs.writeFileSync(path.join(__dirname,"data","js_ptr_"+YEAR+".json"),JSON.stringify(out));
console.log("year",YEAR,"js sites",Object.keys(out).length);
