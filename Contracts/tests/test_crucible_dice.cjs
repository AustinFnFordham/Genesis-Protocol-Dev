"use strict";
/** Offline exact-math / fixture checks only. NEVER touches campaign dice or service. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname,"../examples/crucible_dice_candidate_v0.1.json"),"utf8"));
const { agency_die:AG, entropy_die:EN }=fixture;
function allfaces(d) {assert.deepEqual(Object.keys(d).map(Number),[1,2,3,4,5,6]);}
allfaces(AG); allfaces(EN);
function tally(faces,die) {const t={success:0,cancel_success:0,spark:0,strain:0,resolve_symbol:0,ruin_symbol:0};for(const n of faces){const v=die[n];assert.ok(v,"invalid die face");for(const [k,z] of Object.entries(v))if(k in t)t[k]+=z;}return t;}
function resolve(af,ef) {
 const a=tally(af,AG), b=tally(ef,EN), margin=a.success-b.cancel_success;
 const result={signed_success_margin:margin,success:margin>=1,net_spark:Math.max(0,a.spark-b.strain),net_strain:Math.max(0,b.strain-a.spark),resolve_symbols:a.resolve_symbol,ruin_symbols:b.ruin_symbol};
 assert.ok(result.net_spark===0||result.net_strain===0,"minor symbols did not cancel");
 return result;
}
for(const x of fixture.examples){
 const actual=resolve(x.agency_faces,x.entropy_faces);
 assert.deepEqual(actual,x.expected,"fixture "+x.id);
 if(x.candidate_conversion){
   assert.ok(!fixture.banking.optional_conversion.enabled_by_default);
   assert.ok(actual.net_spark>=x.candidate_conversion.consume_spark);
   assert.equal(actual.net_spark-x.candidate_conversion.consume_spark,x.candidate_conversion.remaining_spark);
 }
}
assert.ok(fixture.guardrails.no_forced_pc_action);
assert.ok(fixture.guardrails.no_automatic_psych_condition_from_any_strain);
assert.ok(!fixture.banking.major_face_auto_banked);
assert.ok(!fixture.conscience_die.implemented && fixture.conscience_die.face_map===null);
assert.ok(!fixture.mastery_d8.implemented && fixture.mastery_d8.face_map===null);
function choose(n,k){let z=1;for(let i=1;i<=k;i++)z=z*(n-i+1)/i;return z;}
function binom(n,k,p){return choose(n,k)*p**k*(1-p)**(n-k);}
function binomialPair(n,m,pA,pB,pred){let z=0;for(let i=0;i<=n;i++)for(let j=0;j<=m;j++)if(pred(i,j))z+=binom(n,i,pA)*binom(m,j,pB);return z;}
function odds(n,m){const success=binomialPair(n,m,4/6,4/6,(a,b)=>a>b);
 const noMinor=binomialPair(n,m,2/6,2/6,(a,b)=>a===b);
 const netSpark3=binomialPair(n,m,2/6,2/6,(a,b)=>a-b>=3);
 const netStrain3=binomialPair(n,m,2/6,2/6,(a,b)=>b-a>=3);
 const anyMajor=1-(5/6)**(n+m);
 return {success,nonzeroMinor:1-noMinor,netSpark3,netStrain3,anyMajor};
}
const expected=[
 {n:3,m:2,success:0.5679012345679012,nonzeroMinor:0.6460905349794237,netSpark3:0.016460905349794237,netStrain3:0,anyMajor:0.598122427983539},
 {n:4,m:2,success:0.7681755829903978,nonzeroMinor:0.7037037037037035,netSpark3:0.05486968449931413,netStrain3:0,anyMajor:0.6651020233196159},
 {n:5,m:2,success:0.8861454046639232,nonzeroMinor:0.7585733882030177,netSpark3:0.11385459533607682,netStrain3:0,anyMajor:0.7209183527663465}
];
for(const e of expected){const z=odds(e.n,e.m);for(const [k,v] of Object.entries(z))assert.ok(Math.abs(v-e[k])<1e-11,`P(${e.n}v${e.m}) ${k} expected ${e[k]} got ${v}`);}
assert.ok(odds(3,2).anyMajor>.59,"automatic major symbols too frequent for unqualified rare banking");
console.log("Crucible candidate fixtures: 5/5 pass; exact probability rows: 3/3 pass; security and schema invariants: pass");
for(const e of expected){const p=odds(e.n,e.m); console.log(`${e.n}v${e.m}: success=${(100*p.success).toFixed(2)}%, nonzeroMinor=${(100*p.nonzeroMinor).toFixed(2)}%, netSpark3=${(100*p.netSpark3).toFixed(2)}%, anyMajor=${(100*p.anyMajor).toFixed(2)}%`);}
