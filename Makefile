# Developer entry points for tabgen. The desktop app lives in desktop/
# (Tauri 2 + React) and runs the Python worker from .venv; see README.md
# and desktop/README.md for requirements.

VENV := .venv/bin

.PHONY: help desktop desktop-build test lint probe

help: ## List the available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-15s %s\n", $$1, $$2}'

desktop: ## Run tabgen Studio in development mode (Vite + app window)
	cd desktop && npm install && npm run tauri dev

desktop-build: ## Build the Linux bundles (.deb and AppImage)
	cd desktop && npm install && npm run tauri build

test: ## Run the Python test suite
	$(VENV)/pytest -q

lint: ## Lint the Python sources
	$(VENV)/ruff check .

probe: ## Run the worker end-to-end probe (downloads models on first run)
	$(VENV)/python scripts/probe_e2e_worker.py
