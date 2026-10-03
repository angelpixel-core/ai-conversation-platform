.PHONY: install install-dev test test-file coverage lint format-check typecheck security check-all docker-up docker-down

# Instalar dependencias base del proyecto
install:
	.venv/bin/python -m pip install -e .

# Instalar dependencias del proyecto incluyendo extras de desarrollo (pytest, ruff, pyright, bandit, etc.)
install-dev:
	.venv/bin/python -m pip install -e ".[dev]"

# Ejecutar linters con Ruff
lint:
	.venv/bin/python -m ruff check src tests

# Formatear código con Ruff
format:
	.venv/bin/python -m ruff format src tests

# Verificar formato del código
format-check:
	.venv/bin/python -m ruff format --check src tests

# Verificación estática de tipos con Pyright
typecheck:
	.venv/bin/python -m pyright

# Análisis estático de seguridad (SAST) con Bandit
security:
	.venv/bin/python -m bandit -r src -s B101

# Auditoría de vulnerabilidades en dependencias
audit:
	.venv/bin/python -m pip_audit --local --skip-editable

# Ejecutar todos los tests (pausando temporalmente el worker si el stack está activo para evitar contención de locks en ChatbotDB)
test:
	@if docker ps --format '{{.Names}}' | grep -q '^chatbot_worker$$'; then \
		docker compose pause worker > /dev/null 2>&1 || true; \
		.venv/bin/python -m pytest; \
		STATUS=$$?; \
		docker compose unpause worker > /dev/null 2>&1 || true; \
		exit $$STATUS; \
	else \
		.venv/bin/python -m pytest; \
	fi

# Ejecutar cobertura de código (reporte en consola y generación de HTML)
coverage:
	.venv/bin/python -m pytest --cov=src --cov-report=term-missing --cov-report=html

# Ejecutar un archivo de test específico. 
# Uso: make test-file FILE=tests/unit/domain/shared/test_aggregate_root.py
test-file:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: Debes proporcionar la ruta del archivo con FILE="; \
		echo "Ejemplo: make test-file FILE=tests/unit/domain/shared/test_aggregate_root.py"; \
		exit 1; \
	fi
	.venv/bin/python -m pytest $(FILE)

# Ejecutar test integral Happy Path del Walkthrough Guide (Steps 1-10)
test-happy-path:
	.venv/bin/python -m pytest tests/integration/test_walkthrough_happy_path.py -v

.PHONY: install install-dev test test-file test-happy-path coverage lint format format-check typecheck security audit check-all docs-build run-api run-worker db/upgrade db/downgrade stack/up stack/up-build stack/down stack/status

# Ejecutar todas las comprobaciones de calidad, tipado, seguridad y tests
check-all: format-check lint typecheck security test

# Generar documentación estática de la API (OpenAPI JSON y ReDoc HTML)
docs-build:
	.venv/bin/python -m src.interfaces.cli.export_openapi

# Ejecutar API FastAPI en modo desarrollo
run-api:
	.venv/bin/uvicorn src.main:app --reload

# Ejecutar Worker de procesamiento de eventos en modo desarrollo
run-worker:
	.venv/bin/python -m src.worker

# Aplicar migraciones pendientes de base de datos
db/upgrade:
	.venv/bin/alembic upgrade head

# Revertir última migración de base de datos
db/downgrade:
	.venv/bin/alembic downgrade -1

# Levantar servicios con Docker Compose (API + Worker + SQL Server + RabbitMQ)
stack/up:
	docker compose up

# Reconstruir y levantar servicios con Docker Compose
stack/up-build:
	docker compose up --build

# Detener servicios de Docker Compose
stack/down:
	docker compose down

# Ver estado de los servicios de Docker Compose
stack/status:
	docker compose ps
