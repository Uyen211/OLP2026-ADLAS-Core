.PHONY: up down build logs ps restart test lint seed clean verify-headers

# Infrastructure commands
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

restart:
	docker compose restart

logs:
	docker compose logs -f

ps:
	docker compose ps

# Development and testing commands
test:
	pytest tests/

lint:
	ruff check backend/app
	cd frontend && pnpm lint

seed:
	python scripts/seed_data.py

verify-headers:
	python scripts/verify_copyright_headers.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
