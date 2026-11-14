PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
RUFF ?= .venv/bin/ruff
NPM ?= npm
COMPOSE ?= docker compose

.PHONY: install install-dev test test-unit test-integration lint format openapi \
	docker-up docker-down docker-logs docker-init listener rbac-test \
	reconciliar reconciliar-catalogo reconciliar-compras rotar-secretos reset \
	frontend-install frontend-dev frontend-build

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
	$(COMPOSE) up -d --build

docker-down:
	$(COMPOSE) down

docker-logs:
	$(COMPOSE) logs -f

docker-init:
	$(COMPOSE) run --rm mongo-init

listener:
	$(PYTHON) scripts/run_listener.py

rbac-test:
	$(COMPOSE) run --rm tools python scripts/verificar_rbac.py

reconciliar: reconciliar-catalogo reconciliar-compras

reconciliar-catalogo:
	$(COMPOSE) run --rm tools python scripts/reconciliar_catalogo.py

reconciliar-compras:
	$(COMPOSE) run --rm tools python scripts/reconciliar_compras.py

rotar-secretos:
	$(COMPOSE) run --rm tools python scripts/rotar_secretos_almacenes.py

# Borra todos los datos de MongoDB. Úsalo solo en desarrollo.
reset:
	$(COMPOSE) down -v

frontend-install:
	cd frontend && $(NPM) ci

frontend-dev:
	cd frontend && $(NPM) run dev

frontend-build:
	cd frontend && $(NPM) run build
