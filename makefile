# ===============================
# CONFIG
# ===============================
PY_DIRS := web/apps web/gtd_calendar
TEST_DIRS := web
MIN_COVERAGE ?= 80

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
	uv run mypy $(PY_DIRS)

test:
	uv run pytest $(TEST_DIRS)

check:
	uv run ruff format --check $(PY_DIRS)
	uv run ruff check $(PY_DIRS)
	uv run mypy $(PY_DIRS)
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
