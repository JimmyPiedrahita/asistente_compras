PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
RUFF ?= .venv/bin/ruff
NPM ?= npm

.PHONY: install install-dev test test-unit test-integration lint format openapi docker-up docker-down docker-logs frontend-install frontend-dev frontend-build

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest tests -q

test-unit:
	$(PYTHON) -m pytest tests/unit -q

test-integration:
	$(PYTHON) -m pytest tests/integration -q

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) check . --fix
	$(RUFF) format .

openapi:
	$(PYTHON) scripts/exportar_openapi.py

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

frontend-install:
	cd frontend && $(NPM) ci

frontend-dev:
	cd frontend && $(NPM) run dev

frontend-build:
	cd frontend && $(NPM) run build
