PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
RUFF ?= .venv/bin/ruff

.PHONY: install install-dev test lint format openapi seed listener reconcile docker-up docker-down docker-seed docker-reconcile

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTHON) -m unittest discover -s tests -t . -v

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) check . --fix
	$(RUFF) format .

openapi:
	$(PYTHON) scripts/exportar_openapi.py

seed:
	$(PYTHON) scripts/seed_mongodb.py

listener:
	$(PYTHON) scripts/run_listener.py

reconcile:
	$(PYTHON) scripts/reconciliar_comparador.py

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-seed:
	docker compose --profile tools run --rm seed

docker-reconcile:
	docker compose exec listener python scripts/reconciliar_comparador.py
