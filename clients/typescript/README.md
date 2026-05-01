# @habeas/client (TypeScript)

Browser- and Node-compatible TypeScript client for the [Habeas Protocol](https://github.com/thehamzaq/habeas-protocol) API.

No runtime dependencies; uses the platform's `fetch`. Node ≥18 has `fetch` global; older Node needs a polyfill.

## Quick start

```ts
import { HabeasClient } from './habeas';

const c = new HabeasClient();          // default: http://127.0.0.1:5544
const h = await c.health();            // { status: { ok: true, judgments: 119 } }

const out = await c.ruleRun(
  'difc_rdc_part_38',
  'StandardBasisAssessment',
  {
    claim: {
      hours_worked: '24',
      hourly_rate_aed: '250',
      reasonable_disbursements_aed: '1121.75',
    },
  },
  { source_label: 'my_typescript_app' },
);
console.log(out.award.total_aed);      // 7121.75

const route = await c.conflictRoute({
  forum: 'SICC',
  originating_forum: 'FOREIGN_ARBITRAL_TRIBUNAL',
  claim_type: 'arbitration_recognition',
});
for (const r of route.recognition_chain) {
  console.log(r.module, r.scope);
}
```

## Errors

```ts
import { HabeasClient, ValidationError, AdminModeRequired } from './habeas';

const c = new HabeasClient();
try {
  await c.ruleValidate('not valid catala');
} catch (e) {
  if (e instanceof ValidationError) {
    console.log(e.payload);             // { ok: false, stage, errors }
  }
}

try {
  await c.ruleSave('my_rule.catala_en', '...');
} catch (e) {
  if (e instanceof AdminModeRequired) {
    console.log('start the server with HABEAS_ADMIN_MODE=1');
  }
}
```

## Endpoint mapping

Every endpoint listed in [`api/openapi.yaml`](../../api/openapi.yaml) is mapped one-to-one to a method on `HabeasClient`. The Python client (`clients/python/habeas`) has the same shape; method names are camelCased here.

## Smoke test

A small Node script exercises every method against a running API:

```bash
node clients/typescript/smoke.mjs
```

Skips gracefully if the API isn't reachable.
