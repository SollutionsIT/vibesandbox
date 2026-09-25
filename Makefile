UV ?= uv
.PHONY: setup images lint typecheck test test-integration demo security build clean
setup:
	$(UV) sync --frozen
images:
	docker build --pull -t vibesandbox-python:0.1.0 docker/python
	docker build --pull -t vibesandbox-node:0.1.0 docker/node
lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .
typecheck:
	$(UV) run mypy src
test:
	$(UV) run pytest tests/unit --cov=vibesandbox --cov-report=term-missing
test-integration:
	$(UV) run pytest tests/integration -v
demo: images
	$(UV) run python scripts/demo.py
security:
	$(UV) run python scripts/audit.py
build:
	$(UV) build
clean:
	$(UV) run python scripts/clean.py
