.PHONY: help typecheck interpret conformance test drift schemas guard-tests property-tests trace-tests api api-docker clean robustness provenance-audit zenodo-tarball

help:
	@echo "Habeas Protocol — make targets:"
	@echo ""
	@echo "  make typecheck       Catala typecheck of every rule module + trace"
	@echo "  make interpret       Catala interpret (run #[test] scopes)"
	@echo "  make conformance     Run all 12 rule conformance tests (Python)"
	@echo "  make trace-tests     Run all 7 trace evaluators (Python)"
	@echo "  make guard-tests     Hostile-input and boundary tests on the Python evaluators"
	@echo "  make property-tests  Run tests/property_tests.py (random invariants)"
	@echo "  make drift           Check rule sources against pinned URL hashes"
	@echo "  make schemas         Regenerate rules/*__*.schema.json from .catala_en"
	@echo "  make test            All of the above (typecheck + conformance + traces + drift + property)"
	@echo "  make api             Start the local HTTP API at :5544"
	@echo "  make api-docker      Build the image and run the API in Docker (loopback only)"
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

# Fails on the first non-zero exit and reports whether the Catala side
# actually ran: a script that only printed its last line used to hide both.
conformance:
	@fail=0; for f in rules/*_conformance.py; do \
	  printf "%-52s " "$$(basename $$f)"; \
	  out=$$(python3 "$$f" 2>&1); rc=$$?; \
	  if echo "$$out" | grep -q "CATALA SKIP"; then cat="catala SKIPPED"; else cat="catala ran"; fi; \
	  if [ $$rc -ne 0 ]; then echo "FAIL ($$cat)"; echo "$$out" | tail -15; fail=1; \
	  else echo "OK ($$cat)"; fi; \
	done; exit $$fail

trace-tests:
	@fail=0; for f in spike/trace-*/evaluate.py; do \
	  printf "%-12s " "$$(dirname $$f | xargs basename)"; \
	  out=$$(python3 "$$f" 2>&1); rc=$$?; \
	  echo "$$out" | tail -1; \
	  if [ $$rc -ne 0 ]; then echo "  ^ exit $$rc"; fail=1; fi; \
	done; exit $$fail

property-tests:
	python3 tests/property_tests.py

guard-tests:
	python3 tests/evaluator_guard_tests.py

drift:
	python3 scripts/check_rule_drift.py --soft

schemas:
	bash scripts/build_rule_schemas.sh

test: typecheck conformance trace-tests guard-tests property-tests provenance-audit

robustness:
	python3 scripts/analyse_robustness.py
	@echo
	@echo "Static robustness analyses written to data/robustness/"
	@echo "API-dependent perturbations (require ANTHROPIC_API_KEY):"
	@echo "  python3 scripts/perturbation_test_retest.py"
	@echo "  python3 scripts/perturbation_tribunal_blind.py"
	@echo "  python3 scripts/perturbation_model_size.py"
	@echo "  python3 scripts/perturbation_prompt_rephrase.py"
	@echo "  python3 scripts/recode_sicc_pr4_claude.py"
	@echo "  python3 scripts/sub_rubric_alternative.py"
	@echo "  python3 scripts/external_correlate.py"

provenance-audit:
	python3 scripts/check_grading_provenance.py

zenodo-tarball:
	@mkdir -p dist
	@VERSION=$$(date -u +%Y%m%d); \
	tar --exclude='dist/*' --exclude='_build' --exclude='_targets' \
	    --exclude='__pycache__' --exclude='data/raw' --exclude='.venv' \
	    --exclude='.git' \
	    -czf dist/habeas-protocol-snapshot-$$VERSION.tar.gz \
	    data rules spike scripts paper.md README.md GRADING_SPEC.md \
	    PREREGISTRATION.md ZENODO.md LICENSE LICENSES CONTRIBUTING.md \
	    SECURITY.md TRADEMARK.md TAKEDOWN.md Makefile Dockerfile \
	    requirements.txt; \
	echo "  → dist/habeas-protocol-snapshot-$$VERSION.tar.gz"
	@echo
	@echo "Next: follow ZENODO.md to deposit and obtain a DOI."

api:
	@echo "Starting stdlib HTTP API at 127.0.0.1:5544"
	@echo "Postgres env first: eval \$$(./scripts/postgres_local.sh env)"
	python3 api/server.py

# The server binds 127.0.0.1 by default, which is unreachable through a
# published container port, so bind 0.0.0.0 inside the container and
# publish on the host's loopback only: the API has no authentication.
api-docker:
	docker build -t habeas .
	docker run --rm -p 127.0.0.1:5544:5544 -e HABEAS_API_HOST=0.0.0.0 habeas \
	  bash -lc 'eval $$(opam env --switch=catala) && python3 api/server.py'

clean:
	rm -rf _build _targets
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
