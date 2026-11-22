// RNG audit for the CC-002 engine dice (noncanonical). node audit/rng_audit.cjs [--json]
// Uses the engine's own roll function on throwaway states: no authoritative dice are touched.
const E = require("../engine.js");
function st(seed) { return { rng: { seed, n: 0 }, receipts: [] }; }
function chi2(counts, expected) { return counts.reduce((a, c) => a + (c - expected) ** 2 / expected, 0); }
const out = {};
// 1. uniformity of d20 within one seed stream (200k)
{ const s = st(20261121), N = 200000, c = Array(20).fill(0); const xs = [];
  for (let i = 0; i < N; i++) { const r = E._rollDice(s, "audit", "u", "1d20").rolls[0]; c[r - 1]++; xs.push(r); }
  s.receipts.length = 0;
  const x2 = chi2(c, N / 20);   // df 19: 99.9% critical value 43.82
  let num = 0, den = 0; const m = xs.reduce((a, b) => a + b, 0) / N;
  for (let i = 0; i < N - 1; i++) num += (xs[i] - m) * (xs[i + 1] - m); for (const x of xs) den += (x - m) ** 2;
  out.single_stream = { rolls: N, chi2_df19: +x2.toFixed(2), critical_999: 43.82, uniform: x2 < 43.82, mean: +m.toFixed(4), expected_mean: 10.5, lag1_autocorrelation: +(num / den).toFixed(5) };
}
// 2. first roll of each of 20k consecutive seeds (the cross-seed case: each fight's first roll)
{ const N = 20000, c = Array(20).fill(0), first = [];
  for (let seed = 1; seed <= N; seed++) { const r = E._rollDice(st(seed), "audit", "u", "1d20").rolls[0]; c[r - 1]++; first.push(r); }
  let same = 0; for (let i = 1; i < N; i++) if (first[i] === first[i - 1]) same++;
  out.across_seeds = { seeds: N, chi2_df19: +chi2(c, N / 20).toFixed(2), uniform: chi2(c, N / 20) < 43.82, neighbour_equal_rate: +(same / (N - 1)).toFixed(4), expected_equal_rate: 0.05 };
}
// 3. advantage / disadvantage means vs exact theory (advantage mean 13.825, disadvantage 7.175)
{ const s = st(7), N = 100000; let a = 0, d = 0;
  for (let i = 0; i < N; i++) { a += E._rollDice(s, "audit", "a", "1d20", { adv: true }).kept; d += E._rollDice(s, "audit", "d", "1d20", { dis: true }).kept; s.receipts.length = 0; }
  out.advantage = { rolls: N, adv_mean: +(a / N).toFixed(3), adv_expected: 13.825, dis_mean: +(d / N).toFixed(3), dis_expected: 7.175 };
}
if (process.argv.includes("--json")) console.log(JSON.stringify(out, null, 1));
else for (const [k, v] of Object.entries(out)) console.log(k, JSON.stringify(v));
module.exports = out;
