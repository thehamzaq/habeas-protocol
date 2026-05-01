// Smoke test for the TypeScript client. Strips types via Node's
// experimental --experimental-strip-types flag (Node ≥22), or falls
// back to a hand-rolled stripped copy if the flag is unsupported.
//
// Run:   node clients/typescript/smoke.mjs
//
// Skips gracefully if the API isn't reachable on 127.0.0.1:5544.

import { execSync } from 'node:child_process';
import { writeFileSync, readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const TS_PATH = join(__dirname, 'habeas.ts');

// Strip `: Type` annotations and `interface`/`type` declarations to
// get a runnable JS module from the .ts source. Crude but enough for
// a single-file client where the type system is purely declarative.
function stripTypes(src) {
  let s = src;
  // Drop entire `interface` / `type` blocks (matches non-nested forms,
  // which is what the client uses).
  s = s.replace(/^export\s+interface\s+\w+\s*(?:extends\s+[^{]+)?\{[\s\S]*?^}/gm, '');
  s = s.replace(/^export\s+type\s+\w+(?:<[^>]+>)?\s*=[^;]+;/gm, '');
  // Generic params on functions / methods.
  s = s.replace(/<\s*[A-Z][\w =,]*?\s*>(?=\s*\()/g, '');
  // Return-type annotations on arrow / function decls.  Best-effort.
  s = s.replace(/\)\s*:\s*Promise<[^=>]+?>(?=\s*[{=])/g, ')');
  s = s.replace(/\)\s*:\s*[A-Z][\w<>\[\]\| ,]*(?=\s*[{=])/g, ')');
  // Param-level annotations: `name: Type` → `name`. Conservative regex
  // that only fires inside parens.
  s = s.replace(/\(([^)]*)\)/g, (_, group) => {
    const cleaned = group.split(',').map(p => {
      const part = p.trim();
      if (!part) return p;
      // Skip rest / default-equals if present
      const eq = part.indexOf('=');
      if (eq >= 0) {
        const lhs = part.slice(0, eq);
        const rhs = part.slice(eq);
        return lhs.replace(/:[^,]+$/, '') + rhs;
      }
      return part.replace(/:[^,]+$/, '');
    }).join(', ');
    return `(${cleaned})`;
  });
  // class-field type annotations `readonly foo: T;`
  s = s.replace(/^(\s*(?:readonly\s+|private\s+|public\s+|protected\s+)*)([\w$]+)\s*:\s*[A-Za-z][\w<>\[\]\|, ]*(?=\s*[;=])/gm, '$1$2');
  return s;
}

async function loadClient() {
  // Prefer Node's native --experimental-strip-types (≥22). When that
  // fails, hand-strip and import from a tempfile.
  try {
    const m = await import(TS_PATH);
    return m;
  } catch (e1) {
    const src = readFileSync(TS_PATH, 'utf8');
    const stripped = stripTypes(src);
    const dir = mkdtempSync(join(tmpdir(), 'habeas-smoke-'));
    const tmpJs = join(dir, 'habeas.mjs');
    writeFileSync(tmpJs, stripped);
    try {
      return await import('file://' + tmpJs);
    } finally {
      try { rmSync(dir, { recursive: true, force: true }); } catch {}
    }
  }
}

let pass = 0, fail = 0;
function check(label, ok, detail = '') {
  if (ok) { pass++; console.log(`  ✓ ${label}`); }
  else    { fail++; console.log(`  ✗ ${label}${detail ? '  — ' + detail : ''}`); }
}

const { HabeasClient, ValidationError, AdminModeRequired } = await loadClient();

const c = new HabeasClient();

// Skip cleanly if the API isn't up.
try {
  const h = await c.health();
  check('health → ok', h.status.ok === true);
} catch (e) {
  console.log(`(API not reachable: ${e.message}) — skipping smoke test.`);
  process.exit(0);
}

// corpus
const j = await c.judgments({ tribunal: 'ADGM', limit: 3 });
check('judgments({tribunal:ADGM,limit:3}) ≤ 3 rows', j.length <= 3 && j.length > 0);
check('every ADGM row has tribunal === "ADGM Courts"', j.every(r => r.tribunal === 'ADGM Courts'));

const tm = await c.tribunalMeans();
check('tribunalMeans() includes DIFC, ADGM, SICC',
      ['DIFC','ADGM','SICC'].every(c => tm.some(m => m.tribunal_code === c)));

// rule library
const mods = await c.ruleModules();
check('ruleModules() ≥ 12', mods.length >= 12);
check('rule library includes sg_iaa_s_31', mods.some(m => m.module === 'sg_iaa_s_31'));

const cs = await c.certificationStates();
check('certificationStates() returns dict ≥ 12', Object.keys(cs).length >= 12);
const allValid = Object.values(cs).every(m =>
  ['draft','submitted','reviewed','certified','deprecated'].includes(m.certification?.state));
check('every certification state is in the spec enum', allValid);

// rule execution
const out = await c.ruleRun('difc_rdc_part_38', 'StandardBasisAssessment', {
  claim: { hours_worked: '24', hourly_rate_aed: '250', reasonable_disbursements_aed: '1121.75' }
}, { source_label: 'ts_smoke' });
check('ruleRun(difc_rdc_part_38) → total_aed === 7121.75',
      Math.abs(out.award.total_aed - 7121.75) < 0.01,
      JSON.stringify(out));

// validate (positive)
try {
  const v = await c.ruleValidate(
    '## tiny\n```catala\ndeclaration scope Tiny:\n  output y content boolean\n\nscope Tiny:\n  definition y equals true\n```\n'
  );
  check('ruleValidate(valid) → ok', v.ok === true);
} catch (e) {
  check('ruleValidate(valid) → ok', false, e.message);
}

// validate (negative)
let raised = false;
try {
  await c.ruleValidate(
    '## broken\n```catala\ndeclaration scope Foo:\n  output y content decimal\n\nscope Foo:\n  definition y equals 1.0 ** 2.0\n```\n'
  );
} catch (e) {
  raised = e instanceof ValidationError;
}
check('ruleValidate(broken) raises ValidationError', raised);

// admin gate
let adminRaised = false;
try {
  await c.ruleSave('sandbox_test_smoke.catala_en',
    '## test\n```catala\ndeclaration scope X:\n  output y content boolean\n\nscope X:\n  definition y equals true\n```\n');
} catch (e) {
  adminRaised = e instanceof AdminModeRequired;
}
check('ruleSave without admin mode → AdminModeRequired', adminRaised);

// routing
const route = await c.conflictRoute({
  forum: 'SICC',
  originating_forum: 'FOREIGN_ARBITRAL_TRIBUNAL',
  claim_type: 'arbitration_recognition',
});
check('conflictRoute(foreign → SICC) recognition chain hits sg_iaa_s_31',
      route.recognition_chain.some(r => r.module === 'sg_iaa_s_31'));

// ingest
const ig = await c.ingest(
  'DIFC Digital Economy Court — DEC 001/2025 Techteryx Ltd v IG Limited dated 3 April 2026. USD 46 million ordered.'
);
check('ingest() extracts case_no DEC 001/2025', ig.case_no === 'DEC 001/2025');
check('ingest() extracts tribunal DIFC Courts', ig.tribunal === 'DIFC Courts');

console.log(`\n${pass}/${pass + fail} TS smoke checks passed`);
process.exit(fail > 0 ? 1 : 0);
