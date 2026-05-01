# habeas (Python)

Stdlib-only Python client for the [Habeas Protocol](https://github.com/thehamzaq/habeas-protocol) API.

## Install

```bash
pip install -e clients/python
```

(No runtime dependencies — uses `urllib.request` from the standard library.)

## Quick start

Start the API server alongside the corpus:

```bash
eval $(./scripts/postgres_local.sh env)
eval $(opam env --switch=catala)
python3 api/server.py
```

Then in Python:

```python
from habeas import HabeasClient

c = HabeasClient()                       # default: http://127.0.0.1:5544
print(c.health())                        # {'status': {'ok': True, 'judgments': 119}}
print(c.tribunal_means())                # paper-headline means

# Run a rule and get the JSON output
out = c.rule_run(
    "difc_rdc_part_38",
    "StandardBasisAssessment",
    {"claim": {"hours_worked": "24",
               "hourly_rate_aed": "250",
               "reasonable_disbursements_aed": "1121.75"}},
    source_label="my_python_script",
)
print(out["award"]["total_aed"])         # 7121.75

# Cross-border routing
route = c.conflict_route(
    forum="SICC",
    originating_forum="FOREIGN_ARBITRAL_TRIBUNAL",
    claim_type="arbitration_recognition",
)
for r in route["recognition_chain"]:
    print(r["module"], r["scope"])
```

## What's exposed

Every endpoint listed in [`api/openapi.yaml`](../../api/openapi.yaml) is mapped one-to-one:

| Method                          | Endpoint                       |
|---------------------------------|--------------------------------|
| `c.health()`                    | `GET /api/health`              |
| `c.judgments(tribunal=, limit=)`| `GET /api/judgments`           |
| `c.rules(limit=)`               | `GET /api/rules`               |
| `c.tribunal_means()`            | `GET /api/tribunal_means`      |
| `c.search(q, limit=)`           | `GET /api/search`              |
| `c.rule_modules()`              | `GET /api/rule_modules`        |
| `c.claims()`                    | `GET /api/claims`              |
| `c.jurisdictions()`             | `GET /api/jurisdictions`       |
| `c.runs_recent(limit=)`         | `GET /api/runs/recent`         |
| `c.runs_stats()`                | `GET /api/runs/stats`          |
| `c.certification_states()`      | `GET /api/certification_states`|
| `c.certification_spec()`        | `GET /api/certification_spec`  |
| `c.rule_run(module, scope, …)`  | `POST /api/rule_run`           |
| `c.rule_validate(source)`       | `POST /api/rule_validate`      |
| `c.rule_save(filename, source)` | `POST /api/rule_save` (admin)  |
| `c.ingest(text)`                | `POST /api/ingest`             |
| `c.conflict_route(…)`           | `POST /api/conflict_route`     |

## Errors

```python
from habeas import HabeasClient, HabeasError, ValidationError, AdminModeRequired

try:
    c.rule_validate("not valid catala")
except ValidationError as e:
    print(e.payload["stage"], e.payload["errors"])

try:
    c.rule_save("my_rule.catala_en", "...")
except AdminModeRequired:
    print("Server must be started with HABEAS_ADMIN_MODE=1.")
```

## Tests

```bash
python3 -m unittest clients/python/tests/test_client.py
```

The tests skip gracefully if the API isn't reachable.
