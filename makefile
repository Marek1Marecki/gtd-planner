# ===============================
# CONFIG
# ===============================
export PYTHONPATH := web
PY_DIRS := web/apps web/gtd_calendar
TEST_DIRS := web
BACKUP_DIR := backups
MIN_COVERAGE ?= 80
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)

# Wczytanie zmiennych z .env jeśli plik istnieje
ifneq ("$(wildcard .env)","")
    include .env
    export
endif

# ===============================
# CORE
# ===============================
.PHONY: help setup format lint type-check test check clean run

help:
	@echo "CORE targets:"
	@echo "  setup        - instalacja zależności i pre-commit"
	@echo "  format       - formatowanie kodu (ruff)"
	@echo "  lint         - linting kodu (ruff)"
	@echo "  type-check   - mypy type checking"
	@echo "  test         - uruchomienie testów"
	@echo "  check        - lokalne CI: format --check + lint + type-check + test"
	@echo "  clean        - usuwa cache i artefakty"
	@echo ""
	@echo "DOCKER targets:"
	@echo "  docker-build - budowa obrazu"
	@echo "  docker-up    - uruchomienie kontenerów"
	@echo "  docker-down  - zatrzymanie kontenerów"
	@echo "  docker-logs  - logi kontenerów"
	@echo "  docker-shell - shell w kontenerze web"
	@echo ""
	@echo "DJANGO targets:"
	@echo "  migrate      - wykonaj migracje"
	@echo "  migrations   - utwórz migracje"
	@echo "  superuser    - utwórz superusera"
	@echo "  shell        - Django shell"
	@echo ""
	@echo "DEV targets:"
	@echo "  add PKG=...  - dodaj zależność"
	@echo "  update       - aktualizacja zależności"
	@echo ""
	@echo "Dostęp: http://localhost:8003"

setup:
	uv sync --extra dev
	uv run pre-commit install

format:
	uv run ruff format $(PY_DIRS)

lint:
	uv run ruff check $(PY_DIRS)

type-check:
	PYTHONPATH=web uv run --env-file .env mypy web/apps web/gtd_calendar

secrets-check:
	@echo "Tier 1: Validating secrets against .env.example..."
	@uv run python -c "import os; from pathlib import Path; \
		example = [l.split('=')[0] for l in Path('.env.example').read_text().splitlines() if '=' in l and not l.startswith('#')]; \
		env = Path('.env').read_text() if Path('.env').exists() else ''; \
		missing = [k for k in example if k not in env]; \
		[print(f'❌ Missing secret: {k}') for k in missing]; \
		exit(1) if missing else print('✅ Secrets validation passed')"

test:
	uv run pytest $(TEST_DIRS)

check:
	uv run ruff format --check $(PY_DIRS)
	uv run ruff check $(PY_DIRS)
	uv run mypy $(PY_DIRS)
	$(MAKE) secrets-check
	uv run pytest $(TEST_DIRS) \
		--cov=. \
		--cov-report=term-missing \
		--cov-fail-under=$(MIN_COVERAGE)

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ coverage.xml

# ===============================
# DOCKER
# ===============================
.PHONY: docker-build docker-up docker-down docker-logs docker-shell

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-shell:
	docker compose exec web bash

docker-scan:
	@echo "Tier 2: Scanning image with Trivy..."
	trivy image --severity CRITICAL,HIGH --ignore-unfixed gtd-planner:latest

test-runtime:
	@echo "Tier 2: Testing Runtime Integrity..."
	@echo "1. Checking whitelist (/tmp is writable)..."
	@docker run --rm --read-only --tmpfs /tmp gtd-planner:latest python -c "open('/tmp/test', 'w').write('ok')"
	@echo "2. Checking blacklist (/app is read-only)..."
	@if docker run --rm --read-only --tmpfs /tmp gtd-planner:latest python -c "open('/app/test', 'w')" 2>&1 | grep -q "Read-only"; then \
		echo "✅ /app is correctly protected"; \
	else \
		echo "❌ SECURITY BREACH: /app is writable!"; exit 1; \
	fi
	@echo "✅ All Runtime Integrity Tests passed"

db-backup:
	@mkdir -p $(BACKUP_DIR)
	docker compose exec -t db pg_dump -U $(POSTGRES_USER) -d $(POSTGRES_DB) > $(BACKUP_DIR)/$(POSTGRES_DB)_$(TIMESTAMP).sql
	@echo "✅ Backup saved to $(BACKUP_DIR)/"

db-restore:
	@if [ -z "$(FILE)" ]; then echo "Usage: make db-restore FILE=backups/file.sql"; exit 1; fi
	cat $(FILE) | docker compose exec -T db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)
	@echo "✅ Restore complete."

# ===============================
# DJANGO
# ===============================
.PHONY: migrate migrations superuser shell

migrate:
	docker compose exec web python manage.py migrate

migrations:
	docker compose exec web python manage.py makemigrations

superuser:
	docker compose exec web python manage.py createsuperuser

shell:
	docker compose exec web python manage.py shell

# ===============================
# DEV UTILITIES
# ===============================
.PHONY: add update lock tree

add:
	@if [ -z "$(PKG)" ]; then echo "Użycie: make add PKG=nazwa_pakietu"; exit 1; fi
	uv add $(PKG)

update:
	uv sync --upgrade

lock:
	uv lock

tree:
	uv tree

# ===============================
# DOCUMENTATION (SPHINX)
# ===============================
.PHONY: docs-clean docs-html

docs-clean:
	rm -rf docs_sphinx/build/*

docs-html:
	@echo "Generowanie dokumentacji Sphinx..."
	PYTHONPATH=web uv run sphinx-build -b html docs_sphinx/source docs_sphinx/build/html