.PHONY: help typecheck interpret conformance test drift schemas property-tests trace-tests api clean

help:
	@echo "Habeas Protocol — make targets:"
	@echo ""
	@echo "  make typecheck       Catala typecheck of every rule module + trace"
	@echo "  make interpret       Catala interpret (run #[test] scopes)"
	@echo "  make conformance     Run all 12 rule conformance tests (Python)"
	@echo "  make trace-tests     Run all 7 trace evaluators (Python)"
	@echo "  make property-tests  Run rules/property_tests.py (random invariants)"
	@echo "  make drift           Check rule sources against pinned URL hashes"
	@echo "  make schemas         Regenerate rules/*__*.schema.json from .catala_en"
	@echo "  make test            All of the above (typecheck + conformance + traces + drift + property)"
	@echo "  make api             Start the local HTTP API at :8000"
	@echo "  make clean           Remove _build/, _targets/, __pycache__/"
	@echo ""
	@echo "Toolchain (install once):"
	@echo "  - Python 3.11+"
	@echo "  - opam + Catala 1.1.0:  opam install catala.1.1.0"
	@echo "  - Python deps:           pip install -r requirements.txt"

CATALA = opam exec -- catala

typecheck:
	@for f in rules/*.catala_en spike/trace-*/rule.catala_en; do \
	  printf "%-60s " "$$f"; \
	  $(CATALA) typecheck --no-stdlib "$$f" 2>&1 | grep -Eo "successful|error" | head -1 || echo "MISSING"; \
	done

interpret:
	@for f in rules/*.catala_en spike/trace-*/rule.catala_en; do \
	  echo "=== $$f ==="; \
	  $(CATALA) interpret --no-stdlib "$$f" 2>&1 | tail -8; \
	done

conformance:
	@for f in rules/*_conformance.py; do \
	  printf "%-60s " "$$(basename $$f)"; \
	  python3 "$$f" 2>&1 | tail -1; \
	done

trace-tests:
	@for f in spike/trace-*/evaluate.py; do \
	  printf "%-60s " "$$(dirname $$f | xargs basename)"; \
	  python3 "$$f" 2>&1 | tail -1; \
	done

property-tests:
	python3 tests/property_tests.py

drift:
	python3 scripts/check_rule_drift.py --soft

schemas:
	bash scripts/build_rule_schemas.sh

test: typecheck conformance trace-tests property-tests

api:
	@echo "Starting stdlib HTTP API at 127.0.0.1:5544"
	@echo "Postgres env first: eval \$$(./scripts/postgres_local.sh env)"
	python3 api/server.py

clean:
	rm -rf _build _targets
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
