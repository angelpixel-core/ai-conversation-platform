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

.PHONY: install install-dev test test-file test-happy-path coverage lint format format-check typecheck security audit check-all docs-build run-api run-worker db/upgrade db/downgrade db/shell stack/up stack/up-d stack/up-build stack/up-build-d stack/down stack/down-v stack/down-clean stack/status stack/logs stack/recreate stack/recreate-build stack/reset stack/reset-build

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

# Abrir consola interactiva SQLCMD en el contenedor de base de datos (MSSQL)
db/shell:
	docker compose exec db /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P 'YourStrong!Passw0rd' -C -d ChatbotDB

# Levantar servicios con Docker Compose en primer plano (API + Worker + DB + Broker)
stack/up:
	docker compose up

# Levantar servicios con Docker Compose en segundo plano (detached mode)
stack/up-d:
	docker compose up -d

# Reconstruir y levantar servicios con Docker Compose en primer plano
stack/up-build:
	docker compose up --build

# Reconstruir y levantar servicios con Docker Compose en segundo plano
stack/up-build-d:
	docker compose up --build -d

# Detener servicios de Docker Compose preservando volúmenes
stack/down:
	docker compose down

# Detener servicios y purgar volúmenes persistentes de datos (DB y Broker)
stack/down-v:
	docker compose down -v

# Alias expresivo para detener servicios y purgar volúmenes de datos
stack/down-clean: stack/down-v

# Ver estado de los servicios de Docker Compose
stack/status:
	docker compose ps

# Seguir los logs de todos los servicios de Docker Compose en tiempo real
stack/logs:
	docker compose logs -f

# Recrear el stack desde cero: purga volúmenes, inicializa DB/Broker, aplica migraciones y levanta la API
stack/recreate: stack/down-v
	@echo "==> Iniciando infraestructura de base de datos y broker..."
	@docker compose up -d db broker
	@echo "==> Aguardando a que SQL Server esté saludable..."
	@until [ "$$(docker inspect --format '{{.State.Health.Status}}' chatbot_db 2>/dev/null)" = "healthy" ]; do \
		sleep 2; \
	done
	@echo "==> Base de datos lista. Aplicando migraciones Alembic..."
	@.venv/bin/alembic upgrade head
	@echo "==> Levantando servicios de API y Worker..."
	docker compose up

# Reconstruir imágenes y recrear el stack desde cero con migraciones aplicadas
stack/recreate-build: stack/down-v
	@echo "==> Iniciando infraestructura de base de datos y broker..."
	@docker compose up -d db broker
	@echo "==> Aguardando a que SQL Server esté saludable..."
	@until [ "$$(docker inspect --format '{{.State.Health.Status}}' chatbot_db 2>/dev/null)" = "healthy" ]; do \
		sleep 2; \
	done
	@echo "==> Base de datos lista. Aplicando migraciones Alembic..."
	@.venv/bin/alembic upgrade head
	@echo "==> Reconstruyendo imágenes y levantando servicios..."
	docker compose up --build

# Alias concisos para recreación del stack
stack/reset: stack/recreate
stack/reset-build: stack/recreate-build
