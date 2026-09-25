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

# Ejecutar todos los tests
test:
	.venv/bin/python -m pytest

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

# Ejecutar todas las verificaciones de calidad y seguridad
check-all: lint format-check typecheck security audit coverage

# Levantar servicios con Docker Compose (API + SQL Server)
docker-up:
	docker compose up -d --build

# Detener servicios de Docker Compose
docker-down:
	docker compose down
