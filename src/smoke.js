/* Run the built page's scripts under a stub DOM.
 *
 * Two things are being checked.  First, that nothing throws -- the page is one
 * 4 MB file and a typo in a rarely-taken branch is otherwise invisible until
 * someone clicks it.  Second, and more usefully, that the pointer-value
 * arithmetic reimplemented in JavaScript agrees with the Python that produced
 * the published composite.  Those are two independent implementations of the
 * same formula; if they disagree, one of them is wrong.
 *
 *     node smoke.js ../index.html
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const file = process.argv[2] || path.join(__dirname, "..", "index.html");
const html = fs.readFileSync(file, "utf8");

const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!blocks.length) { console.error("no script blocks"); process.exit(1); }

/* ---- stubs ---- */
const noop = () => {};
const ctxStub = new Proxy({}, {
  get(t, k) {
    if (k === "canvas") return {width: 800, height: 400};
    if (k === "createLinearGradient") return () => ({addColorStop: noop});
    if (k === "measureText") return () => ({width: 10});
    if (k === "setTransform") return noop;
    return typeof k === "string" ? (t[k] !== undefined ? t[k] : noop) : undefined;
  },
  set(t, k, v) { t[k] = v; return true; }
});
function makeEl(tag) {
  const el = {
    tagName: tag, style: {}, dataset: {}, children: [],
    clientWidth: 900, clientHeight: 400, width: 900, height: 400,
    textContent: "", innerHTML: "", value: "0", max: "100", min: "0",
    className: "", checked: false,
    addEventListener: noop, removeEventListener: noop, dispatchEvent: noop,
    setAttribute: noop, getAttribute: () => null, setPointerCapture: noop,
    classList: {add: noop, remove: noop, toggle: noop, contains: () => false},
    getBoundingClientRect: () => ({left: 0, top: 0, width: 900, height: 400}),
    getContext: () => ctxStub,
    closest: () => null, querySelectorAll: () => [], appendChild: noop,
    focus: noop, blur: noop
  };
  el.parentNode = {
    clientWidth: 900, clientHeight: 400,
    getBoundingClientRect: () => ({left: 0, top: 0, width: 900, height: 400})
  };
  return el;
}
const els = new Map();
const doc = {
  documentElement: {getAttribute: () => null, style: {}},
  getElementById: id => { if (!els.has(id)) els.set(id, makeEl("div")); return els.get(id); },
  querySelectorAll: () => [],
  querySelector: () => null,
  createElement: makeEl,
  addEventListener: noop
};
const sandbox = {
  document: doc, console,
  atob: s => Buffer.from(s, "base64").toString("binary"),
  matchMedia: () => ({matches: false, addEventListener: noop, addListener: noop}),
  getComputedStyle: () => ({getPropertyValue: n => ({
    "--early": "#e8d2ac", "--late": "#8a5f36", "--pith": "#6b4526",
    "--ember": "#b03418", "--sap": "#1f6f6a", "--gold": "#b8860f",
    "--ink": "#241a12", "--ink2": "#6d5844", "--ink3": "#9c8874",
    "--rule": "#ded0bc", "--rule2": "#efe6d9", "--panel2": "#f2e9dc",
    "--grid": "rgba(36,26,18,.09)", "--mono": '"IBM Plex Mono",monospace'
  }[n] || "#888")}),
  devicePixelRatio: 2,
  requestAnimationFrame: noop,
  performance: {now: () => 0},
  addEventListener: noop,
  Float32Array, Int16Array, Uint8Array, Uint16Array, Uint32Array, Float64Array,
  Math, JSON, Map, Set, Array, Object, String, Number, Boolean, Date, isFinite,
  parseInt, parseFloat, Intl, RegExp, Error, Proxy, setTimeout: noop
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

let failed = 0;
blocks.forEach((src, i) => {
  try { vm.runInContext(src, sandbox, {filename: `block${i}.js`}); }
  catch (e) { failed++; console.error(`\n  BLOCK ${i} THREW: ${e.message}\n${(e.stack||"").split("\n").slice(1,4).join("\n")}`); }
});

if (failed) { console.error(`\n${failed} script block(s) threw`); process.exit(1); }
console.log("all %d script blocks executed", blocks.length);

/* ---- cross-check the JS pointer values against the published composite ---- */
// top-level let/const in a vm context live in its global *lexical* scope,
// which is deliberately not reachable as properties of the sandbox object,
// so pull them out by evaluating an expression inside the context.
const {S, PTR, VAL, DEP, NS, COMP, M} =
  vm.runInContext("({S, PTR, VAL, DEP, NS, COMP, M})", sandbox);
console.log("sites %d, values %d", NS, VAL.length);

const C = COMP.all;
let checked = 0, bad = 0, worst = null;
for (let k = 0; k < C.years.length; k += 7) {
  const year = C.years[k];
  let avail = 0, narrow = 0, wide = 0;
  for (let s = 0; s < NS; s++) {
    const i = year - S.y0[s];
    if (i < 0 || i >= S.len[s]) continue;
    const p = PTR[S.off[s] + i];
    if (!isFinite(p)) continue;
    avail++;
    if (p <= -M.threshold) narrow++; else if (p >= M.threshold) wide++;
  }
  checked++;
  if (avail !== C.avail[k] || narrow !== C.narrow[k] || wide !== C.wide[k]) {
    bad++;
    if (!worst) worst = {year, js: [avail, narrow, wide], py: [C.avail[k], C.narrow[k], C.wide[k]]};
  }
}
console.log("pointer cross-check: %d years sampled, %d disagreed with Python", checked, bad);
if (bad) { console.error("  first disagreement:", JSON.stringify(worst)); process.exit(1); }

/* ---- a few named expectations ---- */
const idx = y => C.years.indexOf(y);
const show = y => { const i = idx(y);
  console.log("  %d  narrow %s  wide %s  sites %d", y,
    (100*C.frac[i]).toFixed(1)+"%", (100*C.wfrac[i]).toFixed(1)+"%", C.avail[i]); };
console.log("checkpoints:");
[1258, 1601, 1816, 1912].forEach(show);
const t = C.frac[idx(1258)], u = C.frac[idx(1816)];
if (!(t > 0.2)) { console.error("1258 should be a strong marker year"); process.exit(1); }
if (!(u < 0.10)) { console.error("1816 should NOT be a marker year globally"); process.exit(1); }
console.log("\nOK");
