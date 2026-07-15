.PHONY: help install backend frontend test docker-up docker-down seed lint

help:
	@echo "Available targets:"
	@echo "  install      - Install backend and frontend dependencies"
	@echo "  backend      - Run backend development server"
	@echo "  frontend     - Run frontend development server"
	@echo "  seed         - Seed database with sample cases and enterprises"
	@echo "  test         - Run all tests"
	@echo "  docker-up    - Start full stack with Docker Compose"
	@echo "  docker-down  - Stop Docker Compose stack"
	@echo "  lint         - Run linters"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

seed:
	cd backend && python scripts/seed_data.py

test:
	cd backend && pytest -q
	cd frontend && npm run test

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint
