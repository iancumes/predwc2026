.DEFAULT_GOAL := help
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
WC := $(VENV)/bin/wc2026
API_DIR := services/api
WEB_DIR := apps/web

.PHONY: help setup dev test lint typecheck ingest train backtest simulate freeze \
        report seed-demo clean api web build-web docker-up docker-down fmt

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Create venv and install Python + web deps
	python3 -m venv $(VENV)
	$(PIP) install -q --upgrade pip wheel
	$(PIP) install -q -e "packages/wc2026[db,dev]"
	cd $(WEB_DIR) && npm install
	@echo "Setup complete. Try: make ingest train simulate"

ingest: ## Download + normalise + validate match data
	$(WC) ingest

train: ## Fit and save the production model
	$(WC) train

backtest: ## Walk-forward model comparison (writes artifacts + figures)
	$(PY) scripts/run_backtest.py

simulate: ## Monte Carlo tournament simulation (WC2026_N_SIMS controls count)
	$(WC) simulate --n-sims $${WC2026_N_SIMS:-50000}

freeze: ## Freeze versioned, auditable match predictions
	$(WC) freeze

export: ## Write static JSON for the web app (apps/web/public/data)
	$(PY) scripts/export_static.py

download: ## Fetch the latest international results from the public CC0 feed
	$(PY) scripts/download_data.py

refresh: ## Full auto-update: download -> ingest -> train -> simulate -> freeze -> export
	$(PY) scripts/download_data.py
	$(WC) ingest
	$(WC) train
	$(WC) simulate --n-sims $${WC2026_N_SIMS:-50000}
	$(WC) freeze
	$(PY) scripts/export_static.py

report: ## Consolidated status report
	$(WC) report

seed-demo: ## Run the minimal end-to-end pipeline for a demo (no secrets needed)
	$(WC) ingest && $(WC) train --boosting-iter 150 && $(WC) simulate --n-sims 20000 && $(WC) freeze --boosting-iter 150 && $(WC) report

test: ## Run Python tests (unit, property, integration)
	$(PY) -m pytest packages/wc2026/tests tests -q

lint: ## Ruff lint
	$(VENV)/bin/ruff check packages/wc2026/src scripts services

fmt: ## Ruff autofix
	$(VENV)/bin/ruff check --fix packages/wc2026/src scripts services

typecheck: ## Mypy type check
	$(VENV)/bin/mypy packages/wc2026/src

api: ## Run the FastAPI backend (localhost:8000)
	cd $(API_DIR) && PYTHONPATH=. ../../$(VENV)/bin/uvicorn app.main:app --reload --port 8000

web: ## Run the Next.js frontend (localhost:3000)
	cd $(WEB_DIR) && npm run dev

build-web: ## Production build of the frontend
	cd $(WEB_DIR) && npm run build

dev: ## Reminder for the two dev processes
	@echo "Run 'make api' and 'make web' in two terminals (or 'make docker-up')."

docker-up: ## Build and start the full stack via Docker Compose
	docker compose up --build -d

docker-down: ## Stop and remove the stack (with volumes)
	docker compose down -v

clean: ## Remove caches and build outputs (keeps data/ and artifacts/)
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(WEB_DIR)/.next .pytest_cache .ruff_cache .mypy_cache
