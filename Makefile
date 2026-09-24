.PHONY: install install-dev test test-file coverage docker-up docker-down

# Instalar dependencias base del proyecto
install:
	.venv/bin/python -m pip install -e .

# Instalar dependencias del proyecto incluyendo extras de desarrollo (pytest, pytest-cov, ruff, etc.)
install-dev:
	.venv/bin/python -m pip install -e ".[dev]"

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

# Levantar servicios con Docker Compose (API + SQL Server)
docker-up:
	docker compose up -d --build

# Detener servicios de Docker Compose
docker-down:
	docker compose down
