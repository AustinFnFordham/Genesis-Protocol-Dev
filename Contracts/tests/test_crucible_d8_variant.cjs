"use strict";
// Exact, offline, noncanonical d8 math; no campaign dice, GM tools or storage.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict");
const model=JSON.parse(fs.readFileSync(path.join(__dirname,"../examples/crucible_d8_variant_v0.1.json"),"utf8"));
const a=Object.values(model.agency_faces),e=Object.values(model.entropy_faces);
assert.equal(a.length,8);assert.equal(e.length,8);assert.ok(!model.banking?.major_face_auto_banked);
function result(agency,entropy){
let s=0,x=0,p=0,q,R=0,U=0;
for(const n of agency){const f=a[n-1];assert.ok(f);s+=f.success||0;p+=f.spark||0;R+=f.resolve_symbol||0;}
for(const n of entropy){const f=e[n-1];assert.ok(f);x+=f.cancel_success||0;q+=f.strain||0;U+=f.ruin_symbol||0;}
return {success_margin:s-x,success:s>x,spark:Math.max(0,p-q),strain:Math.max(0,q-p),resolve_symbols:R,ruin_symbols:U};
}
for(const item of model.examples){const got=result(item.agency,item.entropy);assert.deepEqual(got,item.expected,item.id);
if(item.optional_conversion){const isSpark=!!item.optional_conversion.spark_spent;const cost=isSpark?item.optional_conversion.spark_spent:item.optional_conversion.strain_spent;assert.ok((isSpark?got.spark:got.strain)>=cost);}}
function enumerate(sides,n){
 let map=new Map([["0,0,0,0,0,0",{s:0,x:0,p:0,q:0,R:0,U:0,w:1}]]);
 for(let i=0;i<n;i++){const next=new Map();for(const t of map.values())for(const f of sides){const z={s:t.s+(f.success||0),x:t.x+(f.cancel_success||0),p:t.p+(f.spark||0),q:t.q+(f.strain||0),R:t.R+(f.resolve_symbol||0),U:t.U+(f.ruin_symbol||0)};
 const key=Object.values(z).join(",");if(next.has(key))next.get(key).w+=t.w;else next.set(key,{...z,w:t.w});}map=next;}
 return [...map.values()];
}
for(const fixture of model.exact_rates){const [n,m]=fixture.pool.split("v").map(Number);const A=enumerate(a,n),E=enumerate(e,m),den=8**(n+m);
const z={success_pct:0,nonzero_minor_pct:0,spark3_pct:0,strain3_pct:0,resolve_symbol_pct:0,ruin_symbol_pct:0};
for(const t of A)for(const u of E){const p=t.w*u.w/den,net=t.p-u.q;if(t.s>u.x)z.success_pct+=100*p;if(net!==0)z.nonzero_minor_pct+=100*p;if(net>=3)z.spark3_pct+=100*p;if(net<=-3)z.strain3_pct+=100*p;if(t.R)z.resolve_symbol_pct+=100*p;if(u.U)z.ruin_symbol_pct+=100*p;}
for(const [k,v] of Object.entries(z))assert.ok(Math.abs(v-fixture[k])<0.001,k+" "+fixture.pool+" "+v+" != "+fixture[k]);}
console.log("d8 candidate: "+model.examples.length+" deterministic fixtures, "+model.exact_rates.length+" exact probability rows PASS");
