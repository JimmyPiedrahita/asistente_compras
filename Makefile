PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
RUFF ?= .venv/bin/ruff

.PHONY: install install-dev test lint format openapi seed docker-up docker-down docker-seed

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

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-seed:
	docker compose --profile tools run --rm seed
